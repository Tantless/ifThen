from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select

from if_then_mvp.config import get_settings
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    AnalysisJob,
    AppSetting,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    Topic,
)
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.schemas import (
    ConversationRead,
    ImportResponse,
    JobRead,
    MessageRead,
    PersonaProfileRead,
    SegmentRead,
    SettingRead,
    SettingWrite,
    SnapshotRead,
    TopicRead,
)

INVALID_TEXT_DETAIL = "Uploaded file must be valid UTF-8 text"
INVALID_EXPORT_DETAIL = "Uploaded file must be a valid QQ private chat export"


def create_app() -> FastAPI:
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

    @app.get("/jobs/{job_id}", response_model=JobRead)
    def get_job(job_id: int) -> JobRead:
        with session_scope() as session:
            row = session.get(AnalysisJob, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobRead.model_validate(row, from_attributes=True)

    @app.get("/conversations/{conversation_id}/messages", response_model=list[MessageRead])
    def list_messages(
        conversation_id: int,
        limit: int = Query(default=50, ge=1, le=200),
        before: int | None = Query(default=None, ge=1),
        after: int | None = Query(default=None, ge=1),
        keyword: str | None = None,
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
            rows = (
                session.execute(
                    query.order_by(Message.sequence_no.asc()).limit(limit)
                )
                .scalars()
                .all()
            )
            return [MessageRead.model_validate(item, from_attributes=True) for item in rows]

    @app.get("/messages/{message_id}", response_model=MessageRead)
    def get_message(message_id: int) -> MessageRead:
        with session_scope() as session:
            row = session.get(Message, message_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Message not found")
            return MessageRead.model_validate(row, from_attributes=True)

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
                    job=JobRead.model_validate(job, from_attributes=True),
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


def _require_conversation(session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
