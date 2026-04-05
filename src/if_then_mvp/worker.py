from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from if_then_mvp.analysis import (
    build_persona_payload,
    build_segment_summary,
    build_snapshot_payload,
    build_topic_payload,
)
from if_then_mvp.config import get_settings
from if_then_mvp.db import get_sessionmaker
from if_then_mvp.models import (
    AnalysisJob,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Topic,
    TopicLink,
)
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.segmentation import ParsedTimelineMessage, merge_isolated_segments, split_into_segments

_STAGE_PROGRESS = {
    "created": 0,
    "parsing": 10,
    "segmenting": 35,
    "summarizing": 60,
    "topic_persona_snapshot": 85,
    "completed": 100,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_next_queued_job(session) -> AnalysisJob | None:
    return session.execute(
        select(AnalysisJob)
        .where(AnalysisJob.status == "queued", AnalysisJob.job_type == "full_analysis")
        .order_by(AnalysisJob.id.asc())
    ).scalar_one_or_none()


def _claim_next_job() -> tuple[int, int] | None:
    session = get_sessionmaker()()
    try:
        next_job_id = (
            select(AnalysisJob.id)
            .where(AnalysisJob.status == "queued", AnalysisJob.job_type == "full_analysis")
            .order_by(AnalysisJob.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        row = session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == next_job_id, AnalysisJob.status == "queued")
            .values(
                status="running",
                current_stage="parsing",
                progress_percent=_STAGE_PROGRESS["parsing"],
                started_at=_utcnow(),
                finished_at=None,
                error_message=None,
            )
            .returning(AnalysisJob.id, AnalysisJob.conversation_id)
        ).first()
        if row is None:
            session.rollback()
            return None
        session.execute(
            update(Conversation)
            .where(Conversation.id == row.conversation_id)
            .values(status="analyzing")
        )
        session.commit()
        return row.id, row.conversation_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _update_job(job_id: int, **fields) -> None:
    session = get_sessionmaker()()
    try:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            session.rollback()
            return
        for name, value in fields.items():
            setattr(job, name, value)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _update_conversation_status(conversation_id: int, status: str) -> None:
    session = get_sessionmaker()()
    try:
        session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status=status)
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_next_job(*, llm_client) -> bool:
    claim = _claim_next_job()
    if claim is None:
        return False
    job_id, conversation_id = claim

    current_stage = "parsing"
    progress_percent = _STAGE_PROGRESS[current_stage]

    session = get_sessionmaker()()
    try:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            raise RuntimeError(f"Analysis job {job_id} disappeared after claim")

        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise RuntimeError(f"Conversation {conversation_id} was not found")

        import_id = job.payload_json.get("import_id")
        batch = session.get(ImportBatch, import_id)
        if batch is None:
            raise RuntimeError(f"Import batch {import_id} was not found")

        raw_text = Path(batch.source_file_path).read_text(encoding="utf-8")
        parsed = parse_qq_export(text=raw_text, self_display_name=conversation.self_display_name)

        if parsed.messages:
            _delete_existing_analysis_artifacts(session, conversation_id=conversation.id)
            for sequence_no, message in enumerate(parsed.messages, start=1):
                session.add(
                    Message(
                        conversation_id=conversation.id,
                        import_id=batch.id,
                        sequence_no=sequence_no,
                        speaker_name=message.speaker_name,
                        speaker_role=message.speaker_role,
                        timestamp=message.timestamp,
                        content_text=message.content_text,
                        message_type=message.message_type,
                        resource_items=message.resource_items,
                        parse_flags=message.parse_flags,
                        raw_block_text=message.raw_block_text,
                        raw_speaker_label=message.raw_speaker_label,
                        source_line_start=message.source_line_start,
                        source_line_end=message.source_line_end,
                    )
                )
        session.flush()

        current_stage = "segmenting"
        progress_percent = _STAGE_PROGRESS[current_stage]
        job.current_stage = current_stage
        job.progress_percent = progress_percent

        settings = get_settings()
        messages = session.execute(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.sequence_no.asc())
        ).scalars().all()
        timeline = [ParsedTimelineMessage(message.id, message.timestamp, message.speaker_role) for message in messages]
        segments = merge_isolated_segments(
            split_into_segments(timeline, gap_minutes=getattr(settings, "segment_gap_minutes", 30)),
            merge_window_hours=getattr(settings, "isolated_merge_window_hours", 24),
        )
        for draft in segments:
            session.add(
                Segment(
                    conversation_id=conversation.id,
                    start_message_id=draft.message_ids[0],
                    end_message_id=draft.message_ids[-1],
                    start_time=draft.start_time,
                    end_time=draft.end_time,
                    message_count=len(draft.message_ids),
                    self_message_count=draft.self_message_count,
                    other_message_count=draft.other_message_count,
                    segment_kind=draft.segment_kind,
                    source_segment_ids=draft.source_segment_ids or None,
                    source_message_ids=draft.source_message_ids or draft.message_ids,
                )
            )
        session.flush()

        current_stage = "summarizing"
        progress_percent = _STAGE_PROGRESS[current_stage]
        job.current_stage = current_stage
        job.progress_percent = progress_percent

        segment_rows = session.execute(
            select(Segment).where(Segment.conversation_id == conversation.id).order_by(Segment.id.asc())
        ).scalars().all()
        previous_snapshot_summary = None
        for segment in segment_rows:
            segment_messages = [
                {"speaker_role": message.speaker_role, "content_text": message.content_text}
                for message in session.execute(
                    select(Message)
                    .where(Message.id.in_(segment.source_message_ids))
                    .order_by(Message.sequence_no.asc())
                ).scalars()
            ]
            summary = build_segment_summary(
                llm_client=llm_client,
                segment_messages=segment_messages,
                previous_snapshot_summary=previous_snapshot_summary,
            )
            session.add(SegmentSummary(segment_id=segment.id, **summary.model_dump()))
            previous_snapshot_summary = summary.summary_text
        session.flush()

        current_stage = "topic_persona_snapshot"
        progress_percent = _STAGE_PROGRESS[current_stage]
        job.current_stage = current_stage
        job.progress_percent = progress_percent

        summary_pairs = session.execute(
            select(SegmentSummary, Segment)
            .join(Segment, SegmentSummary.segment_id == Segment.id)
            .where(Segment.conversation_id == conversation.id)
            .order_by(Segment.id.asc())
        ).all()
        segment_summaries = [{"summary_text": summary.summary_text} for summary, _segment in summary_pairs]
        evidence_segment_ids = [segment.id for _summary, segment in summary_pairs]

        topic_payload = build_topic_payload(llm_client=llm_client, segment_summaries=segment_summaries)
        topic = Topic(
            conversation_id=conversation.id,
            topic_name=topic_payload.topic_name,
            topic_summary=topic_payload.topic_summary,
            first_seen_at=summary_pairs[0][1].start_time,
            last_seen_at=summary_pairs[-1][1].end_time,
            segment_count=len(summary_pairs),
            topic_status=topic_payload.topic_status,
        )
        session.add(topic)
        session.flush()

        for _summary, segment in summary_pairs:
            session.add(
                TopicLink(
                    topic_id=topic.id,
                    segment_id=segment.id,
                    link_reason=topic_payload.relevance_reason,
                    score=1.0,
                )
            )

        for role in ("self", "other"):
            payload = build_persona_payload(
                llm_client=llm_client,
                subject_role=role,
                segment_summaries=segment_summaries,
            )
            session.add(
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role=role,
                    global_persona_summary=payload.global_persona_summary,
                    style_traits=payload.style_traits,
                    conflict_traits=payload.conflict_traits,
                    relationship_specific_patterns=payload.relationship_specific_patterns,
                    evidence_segment_ids=evidence_segment_ids,
                    confidence=payload.confidence,
                )
            )

        prior_snapshot_summary = None
        for summary, segment in summary_pairs:
            snapshot = build_snapshot_payload(
                llm_client=llm_client,
                segment_summary={"summary_text": summary.summary_text},
                prior_snapshot=prior_snapshot_summary,
            )
            session.add(
                RelationshipSnapshot(
                    conversation_id=conversation.id,
                    as_of_message_id=segment.end_message_id,
                    as_of_time=segment.end_time,
                    **snapshot.model_dump(),
                )
            )
            prior_snapshot_summary = snapshot.snapshot_summary

        conversation.status = "ready"
        job.status = "completed"
        job.current_stage = "completed"
        job.progress_percent = _STAGE_PROGRESS["completed"]
        job.finished_at = _utcnow()
        job.error_message = None
        session.commit()
        return True
    except Exception as exc:
        session.rollback()
        _update_conversation_status(conversation_id, "failed")
        _update_job(
            job_id,
            status="failed",
            current_stage="failed",
            progress_percent=progress_percent,
            finished_at=_utcnow(),
            error_message=str(exc),
        )
        return True
    finally:
        session.close()


def run_forever(*, llm_client, poll_interval_seconds: int = 2) -> None:
    while True:
        processed = run_next_job(llm_client=llm_client)
        if not processed:
            time.sleep(poll_interval_seconds)


def _delete_existing_analysis_artifacts(session, *, conversation_id: int) -> None:
    for snapshot in session.execute(
        select(RelationshipSnapshot).where(RelationshipSnapshot.conversation_id == conversation_id)
    ).scalars():
        session.delete(snapshot)
    for persona in session.execute(
        select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id)
    ).scalars():
        session.delete(persona)
    for topic_link in session.execute(
        select(TopicLink).join(Topic, TopicLink.topic_id == Topic.id).where(Topic.conversation_id == conversation_id)
    ).scalars():
        session.delete(topic_link)
    for topic in session.execute(select(Topic).where(Topic.conversation_id == conversation_id)).scalars():
        session.delete(topic)
    for summary in session.execute(
        select(SegmentSummary).join(Segment, SegmentSummary.segment_id == Segment.id).where(Segment.conversation_id == conversation_id)
    ).scalars():
        session.delete(summary)
    for segment in session.execute(select(Segment).where(Segment.conversation_id == conversation_id)).scalars():
        session.delete(segment)
    for message in session.execute(select(Message).where(Message.conversation_id == conversation_id)).scalars():
        session.delete(message)
    session.flush()
