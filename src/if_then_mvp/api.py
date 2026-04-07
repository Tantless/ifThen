from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import select

from if_then_mvp.config import get_settings
from if_then_mvp.conversation_lifecycle import (
    delete_conversation_tree,
    queue_rerun_analysis,
)
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.llm import ChatJSONClient, LLMClient, LLMClientError
from if_then_mvp.models import (
    AnalysisJob,
    AppSetting,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Simulation,
    SimulationTurn,
    Topic,
    TopicLink,
)
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.retrieval import build_context_pack
from if_then_mvp.runtime_llm import build_runtime_llm_client, load_runtime_settings_map
from if_then_mvp.schemas import (
    ConversationRead,
    ImportResponse,
    JobRead,
    MessageContextRead,
    MessageRead,
    PersonaProfileRead,
    SegmentRead,
    SettingRead,
    SettingWrite,
    SimulationCreate,
    SimulationRead,
    SimulationTurnRead,
    SnapshotRead,
    TopicRead,
)
from if_then_mvp.simulation import assess_branch, generate_first_reply, simulate_short_thread

INVALID_TEXT_DETAIL = "Uploaded file must be valid UTF-8 text"
INVALID_EXPORT_DETAIL = "Uploaded file must be a valid QQ private chat export"


def create_app(*, llm_client: ChatJSONClient | None = None) -> FastAPI:
    app = FastAPI(title="If Then MVP API")

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/conversations", response_model=list[ConversationRead])
    def list_conversations() -> list[ConversationRead]:
        with session_scope() as session:
            rows = session.execute(select(Conversation).order_by(Conversation.id.asc())).scalars().all()
            return [ConversationRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/conversations/{conversation_id}", response_model=ConversationRead)
    def get_conversation(conversation_id: int) -> ConversationRead:
        with session_scope() as session:
            row = session.get(Conversation, conversation_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return ConversationRead.model_validate(row, from_attributes=True)

    @app.delete("/conversations/{conversation_id}", status_code=204)
    def delete_conversation(conversation_id: int) -> Response:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            upload_paths = delete_conversation_tree(session, conversation_id=conversation_id)

        uploads_root = get_settings().data_dir / "uploads"
        for path in upload_paths:
            _remove_managed_file_if_present(path, managed_root=uploads_root)

        return Response(status_code=204)

    @app.get("/jobs/{job_id}", response_model=JobRead)
    def get_job(job_id: int) -> JobRead:
        with session_scope() as session:
            row = session.get(AnalysisJob, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return _job_to_read(row)

    @app.post("/conversations/{conversation_id}/rerun-analysis", response_model=JobRead, status_code=202)
    def rerun_analysis(conversation_id: int) -> JobRead:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            try:
                job = queue_rerun_analysis(session, conversation_id=conversation_id)
            except ValueError as exc:
                detail = str(exc)
                status_code = 409 if detail == "Analysis already queued or running" else 400
                raise HTTPException(status_code=status_code, detail=detail) from exc
            return _job_to_read(job)

    @app.get("/conversations/{conversation_id}/jobs", response_model=list[JobRead])
    def list_conversation_jobs(
        conversation_id: int,
        limit: int = Query(default=10, ge=1, le=50),
    ) -> list[JobRead]:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            rows = (
                session.execute(
                    select(AnalysisJob)
                    .where(AnalysisJob.conversation_id == conversation_id)
                    .order_by(AnalysisJob.id.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [_job_to_read(item) for item in rows]

    @app.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
    def list_messages(
        conversation_id: int,
        limit: int = Query(default=50, ge=1, le=200),
        before: int | None = Query(default=None, ge=1),
        after: int | None = Query(default=None, ge=1),
        keyword: str | None = None,
        order: str = Query(default="asc", pattern="^(asc|desc)$"),
    ) -> list[MessageRead]:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            query = select(Message).where(Message.conversation_id == conversation_id)
            if before is not None:
                query = query.where(Message.sequence_no < before)
            if after is not None:
                query = query.where(Message.sequence_no > after)
            if keyword:
                query = query.where(Message.content_text.contains(keyword))
            order_clause = Message.sequence_no.asc() if order == "asc" else Message.sequence_no.desc()
            rows = session.execute(query.order_by(order_clause).limit(limit)).scalars().all()
            return [MessageRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/messages/{message_id}", response_model=MessageRead)
    def get_message(message_id: int) -> MessageRead:
        with session_scope() as session:
            row = session.get(Message, message_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Message not found")
            return MessageRead.model_validate(row, from_attributes=True)

    @app.get("/messages/{message_id}/context", response_model=MessageContextRead)
    def get_message_context(
        message_id: int,
        radius: int = Query(default=20, ge=1, le=100),
    ) -> MessageContextRead:
        with session_scope() as session:
            target = session.get(Message, message_id)
            if target is None:
                raise HTTPException(status_code=404, detail="Message not found")

            before_rows = (
                session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == target.conversation_id,
                        Message.sequence_no < target.sequence_no,
                    )
                    .order_by(Message.sequence_no.desc())
                    .limit(radius)
                )
                .scalars()
                .all()
            )
            after_rows = (
                session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == target.conversation_id,
                        Message.sequence_no > target.sequence_no,
                    )
                    .order_by(Message.sequence_no.asc())
                    .limit(radius)
                )
                .scalars()
                .all()
            )

            return MessageContextRead(
                target=MessageRead.model_validate(target, from_attributes=True),
                before=[
                    MessageRead.model_validate(item, from_attributes=True)
                    for item in reversed(before_rows)
                ],
                after=[MessageRead.model_validate(item, from_attributes=True) for item in after_rows],
            )

    @app.get("/conversations/{conversation_id}/segments", response_model=list[SegmentRead])
    def list_segments(conversation_id: int) -> list[SegmentRead]:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            rows = session.execute(
                select(Segment).where(Segment.conversation_id == conversation_id).order_by(Segment.id.asc())
            ).scalars().all()
            return [SegmentRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/conversations/{conversation_id}/topics", response_model=list[TopicRead])
    def list_topics(conversation_id: int) -> list[TopicRead]:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            rows = session.execute(select(Topic).where(Topic.conversation_id == conversation_id).order_by(Topic.id.asc())).scalars().all()
            return [TopicRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/conversations/{conversation_id}/profile", response_model=list[PersonaProfileRead])
    def get_profile(conversation_id: int) -> list[PersonaProfileRead]:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            rows = (
                session.execute(
                    select(PersonaProfile)
                    .where(PersonaProfile.conversation_id == conversation_id)
                    .order_by(PersonaProfile.subject_role.asc())
                )
                .scalars()
                .all()
            )
            return [PersonaProfileRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/conversations/{conversation_id}/timeline-state", response_model=SnapshotRead)
    def get_timeline_state(conversation_id: int, at: str) -> SnapshotRead:
        with session_scope() as session:
            _require_conversation(session, conversation_id)
            row = (
                session.execute(
                    select(RelationshipSnapshot)
                .where(
                        RelationshipSnapshot.conversation_id == conversation_id,
                        RelationshipSnapshot.as_of_time <= at,
                    )
                    .join(Message, RelationshipSnapshot.as_of_message_id == Message.id)
                    .order_by(RelationshipSnapshot.as_of_time.desc(), Message.sequence_no.desc())
                )
                .scalars()
                .first()
            )
            if row is None:
                raise HTTPException(status_code=404, detail="No snapshot found before the requested time")
            return SnapshotRead.model_validate(row, from_attributes=True)

    @app.get("/settings", response_model=list[SettingRead])
    def get_settings_entries() -> list[SettingRead]:
        with session_scope() as session:
            rows = session.execute(select(AppSetting).order_by(AppSetting.setting_key.asc())).scalars().all()
            return [SettingRead.model_validate(item, from_attributes=True) for item in rows]

    @app.put("/settings", response_model=SettingRead)
    def put_setting(payload: SettingWrite) -> SettingRead:
        with session_scope() as session:
            row = session.get(AppSetting, payload.setting_key)
            if row is None:
                row = AppSetting(
                    setting_key=payload.setting_key,
                    setting_value=payload.setting_value,
                    is_secret=payload.is_secret,
                )
                session.add(row)
            else:
                row.setting_value = payload.setting_value
                row.is_secret = payload.is_secret
            session.flush()
            return SettingRead.model_validate(row, from_attributes=True)

    @app.post("/simulations", response_model=SimulationRead, status_code=201)
    def create_simulation(payload: SimulationCreate) -> SimulationRead:
        with session_scope() as session:
            _require_conversation(session, payload.conversation_id)

            target_message = session.get(Message, payload.target_message_id)
            if target_message is None or target_message.conversation_id != payload.conversation_id:
                raise HTTPException(status_code=404, detail="Target message not found")

            messages = (
                session.execute(
                    select(Message)
                    .where(Message.conversation_id == payload.conversation_id)
                    .order_by(Message.timestamp.asc(), Message.sequence_no.asc(), Message.id.asc())
                )
                .scalars()
                .all()
            )
            segments = (
                session.execute(
                    select(Segment)
                    .where(Segment.conversation_id == payload.conversation_id)
                    .order_by(Segment.start_time.asc(), Segment.id.asc())
                )
                .scalars()
                .all()
            )
            snapshot = (
                session.execute(
                    select(RelationshipSnapshot)
                    .join(Message, RelationshipSnapshot.as_of_message_id == Message.id)
                    .where(
                        RelationshipSnapshot.conversation_id == payload.conversation_id,
                        (
                            (RelationshipSnapshot.as_of_time < target_message.timestamp)
                            | (
                                (RelationshipSnapshot.as_of_time == target_message.timestamp)
                                & (Message.sequence_no < target_message.sequence_no)
                            )
                        ),
                    )
                    .order_by(RelationshipSnapshot.as_of_time.desc(), Message.sequence_no.desc())
                )
                .scalars()
                .first()
            )
            related_topic_digests = _load_related_topic_digests(
                session=session,
                conversation_id=payload.conversation_id,
                target_message=target_message,
            )
            personas = (
                session.execute(
                    select(PersonaProfile).where(PersonaProfile.conversation_id == payload.conversation_id)
                )
                .scalars()
                .all()
            )
            persona_self = next((item for item in personas if item.subject_role == "self"), None)
            persona_other = next((item for item in personas if item.subject_role == "other"), None)

            try:
                context_pack = build_context_pack(
                    messages=[_message_to_context_dict(item) for item in messages],
                    segments=[_segment_to_context_dict(item) for item in segments],
                    target_message_id=payload.target_message_id,
                    replacement_content=payload.replacement_content,
                    related_topic_digests=related_topic_digests,
                    base_relationship_snapshot=_snapshot_to_context_dict(snapshot),
                    persona_self=_persona_to_context_dict(persona_self),
                    persona_other=_persona_to_context_dict(persona_other),
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            simulation_llm = llm_client or _build_runtime_llm_client(session)
            try:
                assessment = assess_branch(llm_client=simulation_llm, context_pack=context_pack)
                first_reply = generate_first_reply(
                    llm_client=simulation_llm,
                    context_pack=context_pack,
                    assessment=assessment,
                )
                turns = (
                    simulate_short_thread(
                        llm_client=simulation_llm,
                        context_pack=context_pack,
                        assessment=assessment,
                        first_reply=first_reply,
                        turn_count=payload.turn_count,
                    )
                    if payload.mode == "short_thread"
                    else []
                )
            except LLMClientError as exc:
                raise HTTPException(status_code=502, detail="Simulation LLM request failed") from exc

            simulation = Simulation(
                conversation_id=payload.conversation_id,
                target_message_id=payload.target_message_id,
                mode=payload.mode,
                replacement_content=payload.replacement_content,
                context_pack_snapshot=context_pack,
                branch_assessment=assessment,
                first_reply_text=first_reply.first_reply_text,
                impact_summary=assessment["state_shift_summary"],
                status="completed",
            )
            session.add(simulation)
            session.flush()

            turn_rows = []
            for turn in turns:
                turn_row = SimulationTurn(simulation_id=simulation.id, **turn)
                session.add(turn_row)
                turn_rows.append(turn_row)
            session.flush()

            return SimulationRead(
                id=simulation.id,
                mode=simulation.mode,
                replacement_content=simulation.replacement_content,
                first_reply_text=simulation.first_reply_text,
                impact_summary=simulation.impact_summary,
                simulated_turns=[
                    SimulationTurnRead.model_validate(item, from_attributes=True) for item in turn_rows
                ],
            )

    @app.post("/imports/qq-text", response_model=ImportResponse, status_code=201)
    async def import_qq_text(file: UploadFile = File(...), self_display_name: str = Form(...)) -> ImportResponse:
        settings = get_settings()
        raw_bytes = await file.read()

        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail=INVALID_TEXT_DETAIL) from exc

        parsed = parse_qq_export(text=text, self_display_name=self_display_name)
        if parsed.chat_type != "私聊" or not parsed.chat_name or not parsed.messages:
            raise HTTPException(status_code=400, detail=INVALID_EXPORT_DETAIL)

        uploads_dir = settings.data_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        destination = uploads_dir / _generate_storage_name()
        source_file_name = file.filename or "qq_export.txt"

        try:
            destination.write_bytes(raw_bytes)

            with session_scope() as session:
                conversation = Conversation(
                    title=parsed.chat_name,
                    chat_type="private",
                    self_display_name=self_display_name,
                    other_display_name=next(
                        (message.speaker_name for message in parsed.messages if message.speaker_role == "other"),
                        "unknown",
                    ),
                    source_format="qq_chat_exporter_v5",
                    status="queued",
                )
                session.add(conversation)
                session.flush()

                batch = ImportBatch(
                    conversation_id=conversation.id,
                    source_file_name=source_file_name,
                    source_file_path=str(destination),
                    source_file_hash=sha256(raw_bytes).hexdigest(),
                    message_count_hint=parsed.message_count_hint,
                )
                session.add(batch)
                session.flush()

                job = AnalysisJob(
                    conversation_id=conversation.id,
                    job_type="full_analysis",
                    status="queued",
                    current_stage="created",
                    progress_percent=0,
                    retry_count=0,
                    payload_json={"import_id": batch.id},
                )
                session.add(job)
                session.flush()

                response = ImportResponse(
                    conversation=ConversationRead.model_validate(conversation, from_attributes=True),
                    job=_job_to_read(job),
                )
        except Exception:
            _remove_file_if_present(destination)
            raise

        return response

    return app


def _generate_storage_name() -> str:
    return f"qq-import-{uuid4().hex}.txt"


def _remove_file_if_present(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _remove_managed_file_if_present(path: Path, *, managed_root: Path) -> None:
    try:
        resolved_root = managed_root.resolve()
        resolved_path = path.resolve()
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError):
        return

    _remove_file_if_present(resolved_path)


def _require_conversation(session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _message_to_context_dict(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sequence_no": message.sequence_no,
        "timestamp": message.timestamp,
        "speaker_role": message.speaker_role,
        "content_text": message.content_text,
    }


def _segment_to_context_dict(segment: Segment) -> dict[str, object]:
    return {
        "id": segment.id,
        "source_message_ids": segment.source_message_ids or [],
        "start_time": segment.start_time,
        "end_time": segment.end_time,
    }


def _snapshot_to_context_dict(snapshot: RelationshipSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "relationship_temperature": snapshot.relationship_temperature,
        "tension_level": snapshot.tension_level,
        "openness_level": snapshot.openness_level,
        "initiative_balance": snapshot.initiative_balance,
        "defensiveness_level": snapshot.defensiveness_level,
        "relationship_phase": snapshot.relationship_phase,
        "active_sensitive_topics": snapshot.unresolved_conflict_flags,
    }


def _persona_to_context_dict(persona: PersonaProfile | None) -> dict[str, object] | None:
    if persona is None:
        return None
    return {
        "global_persona_summary": persona.global_persona_summary,
        "style_traits": persona.style_traits,
        "conflict_traits": persona.conflict_traits,
        "relationship_specific_patterns": persona.relationship_specific_patterns,
        "confidence": persona.confidence,
    }


def _load_related_topic_digests(
    *,
    session,
    conversation_id: int,
    target_message: Message,
) -> list[dict[str, object]]:
    rows = (
        session.execute(
            select(Topic, TopicLink, Segment, SegmentSummary, Message)
            .join(TopicLink, TopicLink.topic_id == Topic.id)
            .join(Segment, TopicLink.segment_id == Segment.id)
            .join(SegmentSummary, SegmentSummary.segment_id == Segment.id)
            .join(Message, Segment.end_message_id == Message.id)
            .where(
                Topic.conversation_id == conversation_id,
                (
                    (Segment.end_time < target_message.timestamp)
                    | (
                        (Segment.end_time == target_message.timestamp)
                        & (Message.sequence_no < target_message.sequence_no)
                    )
                ),
            )
            .order_by(Topic.id.asc(), Segment.end_time.asc(), Message.sequence_no.asc(), Segment.id.asc())
        )
        .all()
    )
    if not rows:
        return []

    digest_map: dict[int, dict[str, object]] = {}
    for topic, topic_link, segment, segment_summary, _end_message in rows:
        digest = digest_map.setdefault(
            topic.id,
            {
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "cutoff_safe_summary_parts": [],
                "supporting_segment_ids": [],
                "relevance_reason": topic_link.link_reason,
                "topic_status": topic.topic_status,
            },
        )
        digest["cutoff_safe_summary_parts"].append(segment_summary.summary_text)
        digest["supporting_segment_ids"].append(segment.id)

    return [
        {
            "topic_id": topic_id,
            "topic_name": digest["topic_name"],
            "cutoff_safe_summary": " | ".join(digest["cutoff_safe_summary_parts"][:3]),
            "supporting_segment_ids": digest["supporting_segment_ids"],
            "relevance_reason": digest["relevance_reason"],
            "topic_status": digest["topic_status"],
        }
        for topic_id, digest in digest_map.items()
    ]


def _job_to_read(job: AnalysisJob) -> JobRead:
    progress = (job.payload_json or {}).get("progress", {})
    current_stage_total_units = int(progress.get("current_stage_total_units", 0) or 0)
    current_stage_completed_units = int(progress.get("current_stage_completed_units", 0) or 0)
    overall_total_units = int(progress.get("overall_total_units", 0) or 0)
    overall_completed_units = int(progress.get("overall_completed_units", 0) or 0)

    return JobRead(
        id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        current_stage_percent=_calculate_percent(current_stage_completed_units, current_stage_total_units),
        current_stage_total_units=current_stage_total_units,
        current_stage_completed_units=current_stage_completed_units,
        overall_total_units=overall_total_units,
        overall_completed_units=overall_completed_units,
        status_message=progress.get("status_message"),
    )


def _build_runtime_llm_client(session) -> ChatJSONClient:
    settings_map = load_runtime_settings_map(session)
    try:
        return build_runtime_llm_client(role="api", settings_map=settings_map)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Simulation LLM is not configured. "
                "Set llm.base_url, llm.api_key, and llm.chat_model via /settings "
                "or IF_THEN_LLM_BASE_URL / IF_THEN_LLM_API_KEY / IF_THEN_LLM_CHAT_MODEL."
            ),
        ) from exc


def _calculate_percent(completed_units: int, total_units: int) -> int:
    if total_units <= 0:
        return 0
    return min(100, int((completed_units * 100) / total_units))
