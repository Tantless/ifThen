from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select, update

from if_then_mvp.analysis import (
    assign_segment_topics,
    build_topic_creation_payload,
    build_persona_payload,
    build_segment_summary,
    build_snapshot_payload,
    review_topic_merges,
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
    Simulation,
    SimulationJob,
    SimulationTurn,
    Topic,
    TopicLink,
)
from if_then_mvp.parser import ParsedMessage, parse_qq_export
from if_then_mvp.retrieval import build_context_pack
from if_then_mvp.runtime_llm import build_runtime_llm_client, load_runtime_settings_map
from if_then_mvp.segmentation import ParsedTimelineMessage, SegmentDraft, merge_isolated_segments, split_into_segments
from if_then_mvp.simulation import assess_branch, generate_first_reply, simulate_short_thread
from if_then_mvp.simulation_jobs import (
    SimulationProgressSnapshot,
    apply_simulation_job_progress,
    claim_next_simulation_job,
)

_PARSING_BATCH_SIZE = 500
_SEGMENT_BATCH_SIZE = 100
_SUMMARY_BATCH_SIZE = 10
_SNAPSHOT_BATCH_SIZE = 10
_PROGRESS_INTERVAL_SECONDS = 30
_STAGE_THRESHOLDS = {
    "parsing": _PARSING_BATCH_SIZE,
    "segmenting": _SEGMENT_BATCH_SIZE,
    "summarizing": _SUMMARY_BATCH_SIZE,
    "topic_persona_snapshot": _SNAPSHOT_BATCH_SIZE,
    "completed": 1,
    "failed": 1,
}


@dataclass(slots=True)
class ProgressSnapshot:
    job_id: int
    current_stage: str
    progress_percent: int
    current_stage_completed_units: int
    current_stage_total_units: int
    overall_completed_units: int
    overall_total_units: int
    status_message: str
    elapsed_seconds: float | None = None


class AnalysisPerformanceTracker:
    def __init__(self, *, time_fn: Callable[[], float]) -> None:
        self._time_fn = time_fn
        self._started_at = time_fn()
        self._finished_at: float | None = None
        self._current_stage: str | None = None
        self._stage_started_at: float | None = None
        self._stage_elapsed_seconds: dict[str, float] = {}
        self._llm_call_counts: dict[str, int] = {}
        self._input_counts: dict[str, int] = {}

    def set_input_counts(self, *, messages: int, segments: int) -> None:
        self._input_counts = {
            "messages": messages,
            "segments": segments,
        }

    def start_stage(self, stage: str) -> None:
        self._close_current_stage()
        self._current_stage = stage
        self._stage_started_at = self._time_fn()

    def record_llm_call(self, call_type: str) -> None:
        self._llm_call_counts[call_type] = self._llm_call_counts.get(call_type, 0) + 1

    def finish(self) -> None:
        self._close_current_stage()
        self._finished_at = self._time_fn()

    def snapshot(self) -> dict[str, object]:
        now = self._finished_at if self._finished_at is not None else self._time_fn()
        stage_elapsed_seconds = dict(self._stage_elapsed_seconds)
        if self._current_stage is not None and self._stage_started_at is not None:
            stage_elapsed_seconds[self._current_stage] = (
                stage_elapsed_seconds.get(self._current_stage, 0.0)
                + max(0.0, now - self._stage_started_at)
            )

        llm_call_counts = dict(self._llm_call_counts)
        llm_call_counts["total"] = sum(self._llm_call_counts.values())

        return {
            "elapsed_seconds": _round_seconds(max(0.0, now - self._started_at)),
            "current_stage": self._current_stage,
            "input_counts": dict(self._input_counts),
            "llm_call_counts": llm_call_counts,
            "stage_elapsed_seconds": {
                stage: _round_seconds(seconds)
                for stage, seconds in stage_elapsed_seconds.items()
            },
        }

    def _close_current_stage(self) -> None:
        if self._current_stage is None or self._stage_started_at is None:
            return
        elapsed = max(0.0, self._time_fn() - self._stage_started_at)
        self._stage_elapsed_seconds[self._current_stage] = (
            self._stage_elapsed_seconds.get(self._current_stage, 0.0) + elapsed
        )
        self._current_stage = None
        self._stage_started_at = None


@dataclass(slots=True)
class ConsoleProgressReporter:
    printer: Callable[[str], None] = print
    time_fn: Callable[[], float] = time.monotonic
    max_interval_seconds: int = _PROGRESS_INTERVAL_SECONDS
    _last_stage: str | None = None
    _last_stage_completed_units: int = 0
    _last_emit_at: float | None = None

    def maybe_emit(self, snapshot: ProgressSnapshot) -> None:
        now = self.time_fn()
        threshold = _STAGE_THRESHOLDS.get(snapshot.current_stage, 1)
        should_emit = False

        if self._last_emit_at is None:
            should_emit = True
        elif snapshot.current_stage != self._last_stage:
            should_emit = True
        elif snapshot.current_stage in {"completed", "failed"}:
            should_emit = True
        elif snapshot.current_stage_completed_units >= snapshot.current_stage_total_units > 0:
            should_emit = True
        elif snapshot.current_stage_completed_units - self._last_stage_completed_units >= threshold:
            should_emit = True
        elif now - self._last_emit_at >= self.max_interval_seconds:
            should_emit = True

        if not should_emit:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        stage_percent = _calculate_percent(
            snapshot.current_stage_completed_units,
            snapshot.current_stage_total_units,
        )
        elapsed_seconds = getattr(snapshot, "elapsed_seconds", None)
        elapsed_part = "" if elapsed_seconds is None else f" elapsed={elapsed_seconds:.1f}s"
        self.printer(
            f"[{timestamp}] job={snapshot.job_id} stage={snapshot.current_stage} "
            f"overall={snapshot.progress_percent}% stage_progress={stage_percent}% "
            f"{snapshot.status_message}{elapsed_part}"
        )
        self._last_stage = snapshot.current_stage
        self._last_stage_completed_units = snapshot.current_stage_completed_units
        self._last_emit_at = now


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _round_seconds(value: float) -> float:
    return round(value, 3)


def _load_next_queued_job(session) -> AnalysisJob | None:
    return session.execute(
        select(AnalysisJob)
        .where(AnalysisJob.status == "queued", AnalysisJob.job_type.in_(["full_analysis", "import_only"]))
        .order_by(AnalysisJob.id.asc())
    ).scalar_one_or_none()


def _claim_next_job() -> tuple[int, int] | None:
    session = get_sessionmaker()()
    try:
        next_job_id = (
            select(AnalysisJob.id)
            .where(AnalysisJob.status == "queued", AnalysisJob.job_type.in_(["full_analysis", "import_only"]))
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
                progress_percent=0,
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


def _build_worker_runtime_llm_client():
    session = get_sessionmaker()()
    try:
        return build_runtime_llm_client(
            role="worker",
            settings_map=load_runtime_settings_map(session),
        )
    finally:
        session.close()


def _peek_next_queued_job_type() -> str | None:
    session = get_sessionmaker()()
    try:
        row = _load_next_queued_job(session)
        return row.job_type if row is not None else None
    finally:
        session.close()


def run_next_job(*, llm_client=None, progress_reporter: ConsoleProgressReporter | None = None) -> bool:
    effective_llm = llm_client
    next_job_type = _peek_next_queued_job_type()

    if next_job_type is None:
        return False

    requires_llm = next_job_type != "import_only"

    if effective_llm is None and requires_llm:
        try:
            effective_llm = _build_worker_runtime_llm_client()
        except RuntimeError:
            return False

    claim = _claim_next_job()
    if claim is None:
        return False
    job_id, conversation_id = claim
    progress_reporter = progress_reporter or ConsoleProgressReporter()
    performance_tracker = AnalysisPerformanceTracker(time_fn=progress_reporter.time_fn)
    latest_snapshot = ProgressSnapshot(
        job_id=job_id,
        current_stage="parsing",
        progress_percent=0,
        current_stage_completed_units=0,
        current_stage_total_units=0,
        overall_completed_units=0,
        overall_total_units=0,
        status_message="parsing 0/0 messages",
    )

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

        performance_tracker.start_stage("parsing")
        raw_text = Path(batch.source_file_path).read_text(encoding="utf-8")
        parsed = parse_qq_export(text=raw_text, self_display_name=conversation.self_display_name)
        settings = get_settings()
        preview_segments = _preview_segments(
            parsed_messages=parsed.messages,
            gap_minutes=getattr(settings, "segment_gap_minutes", 30),
            merge_window_hours=getattr(settings, "isolated_merge_window_hours", 24),
        )
        message_count = len(parsed.messages)
        segment_count = len(preview_segments)
        overall_total_units = _calculate_overall_total_units(
            message_count=message_count,
            segment_count=segment_count,
        )
        performance_tracker.set_input_counts(messages=message_count, segments=segment_count)

        _delete_existing_analysis_artifacts(session, conversation_id=conversation.id)
        latest_snapshot = _apply_progress(
            job,
            current_stage="parsing",
            current_stage_completed_units=0,
            current_stage_total_units=message_count,
            overall_completed_units=0,
            overall_total_units=overall_total_units,
            status_message=f"parsing 0/{message_count} messages",
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        sequence_to_message_id: dict[int, int] = {}
        for batch_start in range(0, message_count, _PARSING_BATCH_SIZE):
            batch_messages = parsed.messages[batch_start : batch_start + _PARSING_BATCH_SIZE]
            persisted_rows: list[Message] = []
            for sequence_no, message in enumerate(batch_messages, start=batch_start + 1):
                row = Message(
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
                session.add(row)
                persisted_rows.append(row)
            session.flush()
            for row in persisted_rows:
                sequence_to_message_id[row.sequence_no] = row.id
            completed_messages = min(batch_start + len(batch_messages), message_count)
            latest_snapshot = _apply_progress(
                job,
                current_stage="parsing",
                current_stage_completed_units=completed_messages,
                current_stage_total_units=message_count,
                overall_completed_units=completed_messages,
                overall_total_units=overall_total_units,
                status_message=f"parsing {completed_messages}/{message_count} messages",
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        if job.job_type == "import_only":
            conversation.status = "imported"
            performance_tracker.finish()
            latest_snapshot = _apply_progress(
                job,
                current_stage="completed",
                current_stage_completed_units=message_count,
                current_stage_total_units=message_count,
                overall_completed_units=message_count,
                overall_total_units=message_count,
                status_message=f"imported {message_count} messages",
                status="completed",
                finished_at=_utcnow(),
                error_message=None,
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)
            return True

        actual_segments = [
            _materialize_segment_draft(preview_segment, sequence_to_message_id)
            for preview_segment in preview_segments
        ]

        performance_tracker.start_stage("segmenting")
        latest_snapshot = _apply_progress(
            job,
            current_stage="segmenting",
            current_stage_completed_units=0,
            current_stage_total_units=segment_count,
            overall_completed_units=message_count,
            overall_total_units=overall_total_units,
            status_message=f"segmenting 0/{segment_count} segments",
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        for batch_start in range(0, segment_count, _SEGMENT_BATCH_SIZE):
            batch_segments = actual_segments[batch_start : batch_start + _SEGMENT_BATCH_SIZE]
            for draft in batch_segments:
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
            completed_segments = min(batch_start + len(batch_segments), segment_count)
            latest_snapshot = _apply_progress(
                job,
                current_stage="segmenting",
                current_stage_completed_units=completed_segments,
                current_stage_total_units=segment_count,
                overall_completed_units=message_count + completed_segments,
                overall_total_units=overall_total_units,
                status_message=f"segmenting {completed_segments}/{segment_count} segments",
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        segment_rows = session.execute(
            select(Segment).where(Segment.conversation_id == conversation.id).order_by(Segment.id.asc())
        ).scalars().all()
        performance_tracker.start_stage("summarizing")
        latest_snapshot = _apply_progress(
            job,
            current_stage="summarizing",
            current_stage_completed_units=0,
            current_stage_total_units=segment_count,
            overall_completed_units=message_count + segment_count,
            overall_total_units=overall_total_units,
            status_message=f"summarizing 0/{segment_count} summaries",
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        previous_snapshot_summary = None
        for index, segment in enumerate(segment_rows, start=1):
            segment_messages = [
                {"speaker_role": message.speaker_role, "content_text": message.content_text}
                for message in session.execute(
                    select(Message)
                    .where(Message.id.in_(segment.source_message_ids))
                    .order_by(Message.sequence_no.asc())
                ).scalars()
            ]
            performance_tracker.record_llm_call("segment_summary")
            summary = build_segment_summary(
                llm_client=effective_llm,
                segment_messages=segment_messages,
                previous_snapshot_summary=previous_snapshot_summary,
            )
            session.add(SegmentSummary(segment_id=segment.id, **summary.model_dump()))
            previous_snapshot_summary = summary.summary_text
            session.flush()
            latest_snapshot = _apply_progress(
                job,
                current_stage="summarizing",
                current_stage_completed_units=index,
                current_stage_total_units=segment_count,
                overall_completed_units=message_count + segment_count + index,
                overall_total_units=overall_total_units,
                status_message=f"summarizing {index}/{segment_count} summaries",
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        summary_pairs = session.execute(
            select(SegmentSummary, Segment)
            .join(Segment, SegmentSummary.segment_id == Segment.id)
            .where(Segment.conversation_id == conversation.id)
            .order_by(Segment.id.asc())
        ).all()
        segment_summaries = [_segment_summary_payload(summary) for summary, _segment in summary_pairs]
        evidence_segment_ids = [segment.id for _summary, segment in summary_pairs]
        topic_stage_total_units = (2 * segment_count) + 3
        topic_stage_base_units = message_count + (2 * segment_count)

        performance_tracker.start_stage("topic_resolution")
        latest_snapshot = _apply_progress(
            job,
            current_stage="topic_persona_snapshot",
            current_stage_completed_units=0,
            current_stage_total_units=topic_stage_total_units,
            overall_completed_units=topic_stage_base_units,
            overall_total_units=overall_total_units,
            status_message=f"topic_persona_snapshot 0/{topic_stage_total_units} tasks",
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        topics_by_id: dict[int, Topic] = {}
        completed_topic_stage_units = 0
        for index, (summary, segment) in enumerate(summary_pairs, start=1):
            current_segment_summary = _segment_summary_payload(summary)
            performance_tracker.record_llm_call("topic_assignment")
            assignment = assign_segment_topics(
                llm_client=effective_llm,
                current_segment_summary=current_segment_summary,
                existing_topics=[_topic_prompt_payload(topic) for topic in topics_by_id.values()],
            )
            matched_topics = _normalize_topic_matches(
                matched_topics=assignment.matched_topics,
                existing_topic_ids=set(topics_by_id.keys()),
            )
            linked_topic_ids: set[int] = set()

            for match in matched_topics:
                topic = topics_by_id[match.topic_id]
                created = _ensure_topic_link(
                    session,
                    topic_id=topic.id,
                    segment_id=segment.id,
                    link_reason=match.link_reason,
                    score=match.score,
                )
                if created:
                    _touch_topic_with_segment(topic, segment)
                linked_topic_ids.add(topic.id)

            if assignment.should_create_new_topic or not linked_topic_ids:
                performance_tracker.record_llm_call("topic_creation")
                creation = build_topic_creation_payload(
                    llm_client=effective_llm,
                    current_segment_summary=current_segment_summary,
                )
                topic = Topic(
                    conversation_id=conversation.id,
                    topic_name=creation.topic_name,
                    topic_summary=creation.topic_summary,
                    first_seen_at=segment.start_time,
                    last_seen_at=segment.end_time,
                    segment_count=1,
                    topic_status=creation.topic_status,
                )
                session.add(topic)
                session.flush()
                topics_by_id[topic.id] = topic
                _ensure_topic_link(
                    session,
                    topic_id=topic.id,
                    segment_id=segment.id,
                    link_reason=creation.relevance_reason,
                    score=1.0,
                )

            session.flush()
            completed_topic_stage_units = index
            latest_snapshot = _apply_progress(
                job,
                current_stage="topic_persona_snapshot",
                current_stage_completed_units=completed_topic_stage_units,
                current_stage_total_units=topic_stage_total_units,
                overall_completed_units=topic_stage_base_units + completed_topic_stage_units,
                overall_total_units=overall_total_units,
                status_message=(
                    f"topic_persona_snapshot {completed_topic_stage_units}/{topic_stage_total_units} "
                    f"tasks (topic resolution {index}/{segment_count})"
                ),
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        performance_tracker.start_stage("topic_merge_review")
        performance_tracker.record_llm_call("topic_merge_review")
        merge_review = review_topic_merges(
            llm_client=effective_llm,
            topics=[_topic_prompt_payload(topic) for topic in topics_by_id.values()],
        )
        topics_by_id = _apply_topic_merges(
            session,
            topics_by_id=topics_by_id,
            merge_decisions=merge_review.merges,
        )
        session.flush()
        completed_topic_stage_units += 1
        latest_snapshot = _apply_progress(
            job,
            current_stage="topic_persona_snapshot",
            current_stage_completed_units=completed_topic_stage_units,
            current_stage_total_units=topic_stage_total_units,
            overall_completed_units=topic_stage_base_units + completed_topic_stage_units,
            overall_total_units=overall_total_units,
            status_message=(
                f"topic_persona_snapshot {completed_topic_stage_units}/{topic_stage_total_units} "
                "tasks (topic merge review)"
            ),
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        performance_tracker.start_stage("persona")
        for role in ("self", "other"):
            performance_tracker.record_llm_call("persona")
            payload = build_persona_payload(
                llm_client=effective_llm,
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
            completed_topic_stage_units += 1
            session.flush()
            latest_snapshot = _apply_progress(
                job,
                current_stage="topic_persona_snapshot",
                current_stage_completed_units=completed_topic_stage_units,
                current_stage_total_units=topic_stage_total_units,
                overall_completed_units=topic_stage_base_units + completed_topic_stage_units,
                overall_total_units=overall_total_units,
                status_message=(
                    f"topic_persona_snapshot {completed_topic_stage_units}/{topic_stage_total_units} "
                    f"tasks (persona {role})"
                ),
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        performance_tracker.start_stage("snapshots")
        prior_snapshot_summary = None
        for index, (summary, segment) in enumerate(summary_pairs, start=1):
            performance_tracker.record_llm_call("relationship_snapshot")
            snapshot = build_snapshot_payload(
                llm_client=effective_llm,
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
            session.flush()
            total_completed = completed_topic_stage_units + index
            latest_snapshot = _apply_progress(
                job,
                current_stage="topic_persona_snapshot",
                current_stage_completed_units=total_completed,
                current_stage_total_units=topic_stage_total_units,
                overall_completed_units=topic_stage_base_units + total_completed,
                overall_total_units=overall_total_units,
                status_message=(
                    f"topic_persona_snapshot {total_completed}/{topic_stage_total_units} "
                    f"tasks (snapshots {index}/{segment_count})"
                ),
                performance=performance_tracker.snapshot(),
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

        performance_tracker.start_stage("finalizing")
        conversation.status = "ready"
        performance_tracker.finish()
        latest_snapshot = _apply_progress(
            job,
            current_stage="completed",
            current_stage_completed_units=overall_total_units,
            current_stage_total_units=overall_total_units,
            overall_completed_units=overall_total_units,
            overall_total_units=overall_total_units,
            status_message=f"completed {overall_total_units}/{overall_total_units} units",
            status="completed",
            finished_at=_utcnow(),
            error_message=None,
            performance=performance_tracker.snapshot(),
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)
        return True
    except Exception as exc:
        session.rollback()
        performance_tracker.finish()
        failed_performance = performance_tracker.snapshot()
        _cleanup_failed_job_artifacts(
            job_id=job_id,
            conversation_id=conversation_id,
            latest_snapshot=latest_snapshot,
            error_message=str(exc),
            performance=failed_performance,
        )
        failed_snapshot = ProgressSnapshot(
            job_id=job_id,
            current_stage="failed",
            progress_percent=latest_snapshot.progress_percent,
            current_stage_completed_units=latest_snapshot.current_stage_completed_units,
            current_stage_total_units=latest_snapshot.current_stage_total_units,
            overall_completed_units=latest_snapshot.overall_completed_units,
            overall_total_units=latest_snapshot.overall_total_units,
            status_message=f"failed {latest_snapshot.status_message}: {exc}",
            elapsed_seconds=_performance_elapsed_seconds(failed_performance),
        )
        progress_reporter.maybe_emit(failed_snapshot)
        return True
    finally:
        session.close()


def run_next_simulation_job(*, llm_client=None) -> bool:
    effective_llm = llm_client
    if effective_llm is None:
        try:
            effective_llm = _build_worker_runtime_llm_client()
        except RuntimeError:
            return False

    session = get_sessionmaker()()
    progress_reporter = ConsoleProgressReporter()
    latest_snapshot = SimulationProgressSnapshot(
        job_id=0,
        current_stage="branch_assessment",
        progress_percent=0,
        current_stage_completed_units=0,
        current_stage_total_units=1,
        overall_completed_units=0,
        overall_total_units=1,
        status_message="branch_assessment 0/1 step",
    )
    job_id: int | None = None
    try:
        job = claim_next_simulation_job(session)
        if job is None:
            return False
        job_id = job.id
        latest_snapshot = _simulation_snapshot_from_job(job)
        progress_reporter.maybe_emit(latest_snapshot)

        conversation = session.get(Conversation, job.conversation_id)
        if conversation is None:
            raise RuntimeError(f"Conversation {job.conversation_id} was not found")

        target_message = session.get(Message, job.target_message_id)
        if target_message is None:
            raise RuntimeError(f"Target message {job.target_message_id} was not found")

        context_pack = _build_simulation_context_pack(
            session,
            conversation_id=job.conversation_id,
            target_message=target_message,
            replacement_content=job.replacement_content,
        )
        total_units = _calculate_simulation_total_units(job.turn_count)

        latest_snapshot = apply_simulation_job_progress(
            job,
            current_stage="branch_assessment",
            current_stage_completed_units=0,
            current_stage_total_units=1,
            overall_completed_units=0,
            overall_total_units=total_units,
            status_message="branch_assessment 0/1 step",
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        assessment = assess_branch(llm_client=effective_llm, context_pack=context_pack)

        latest_snapshot = apply_simulation_job_progress(
            job,
            current_stage="branch_assessment",
            current_stage_completed_units=1,
            current_stage_total_units=1,
            overall_completed_units=1,
            overall_total_units=total_units,
            status_message="branch_assessment 1/1 step",
        )
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)

        first_reply: object | None = None
        turns: list[dict[str, object]] = []

        if job.turn_count > 0:
            latest_snapshot = apply_simulation_job_progress(
                job,
                current_stage="first_reply",
                current_stage_completed_units=0,
                current_stage_total_units=1,
                overall_completed_units=1,
                overall_total_units=total_units,
                status_message="first_reply 0/1 turn",
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

            first_reply = generate_first_reply(
                llm_client=effective_llm,
                context_pack=context_pack,
                assessment=assessment,
            )

            latest_snapshot = apply_simulation_job_progress(
                job,
                current_stage="first_reply",
                current_stage_completed_units=1,
                current_stage_total_units=1,
                overall_completed_units=2,
                overall_total_units=total_units,
                status_message="first_reply 1/1 turn",
            )
            session.commit()
            progress_reporter.maybe_emit(latest_snapshot)

            if job.mode == "short_thread":
                if job.turn_count > 1:
                    latest_snapshot = apply_simulation_job_progress(
                        job,
                        current_stage="short_thread",
                        current_stage_completed_units=0,
                        current_stage_total_units=job.turn_count - 1,
                        overall_completed_units=2,
                        overall_total_units=total_units,
                        status_message=f"short_thread 0/{job.turn_count - 1} turns",
                    )
                    session.commit()
                    progress_reporter.maybe_emit(latest_snapshot)
                    turns = simulate_short_thread(
                        llm_client=effective_llm,
                        context_pack=context_pack,
                        assessment=assessment,
                        first_reply=first_reply,
                        turn_count=job.turn_count - 1,
                    )
                    latest_snapshot = apply_simulation_job_progress(
                        job,
                        current_stage="short_thread",
                        current_stage_completed_units=max(job.turn_count - 1, 0),
                        current_stage_total_units=max(job.turn_count - 1, 0),
                        overall_completed_units=total_units,
                        overall_total_units=total_units,
                        status_message=f"short_thread {max(job.turn_count - 1, 0)}/{max(job.turn_count - 1, 0)} turns",
                    )
                    session.commit()
                    progress_reporter.maybe_emit(latest_snapshot)
        simulation = Simulation(
            conversation_id=job.conversation_id,
            target_message_id=job.target_message_id,
            mode=job.mode,
            replacement_content=job.replacement_content,
            context_pack_snapshot=context_pack,
            branch_assessment=assessment,
            first_reply_text=(first_reply.first_reply_text if first_reply is not None else None),
            impact_summary=assessment.get("state_shift_summary"),
            status="completed",
            error_message=None,
        )
        session.add(simulation)
        session.flush()

        if turns:
            for turn in turns:
                session.add(
                    SimulationTurn(
                        simulation_id=simulation.id,
                        turn_index=int(turn["turn_index"]),
                        speaker_role=str(turn["speaker_role"]),
                        message_text=str(turn["message_text"]),
                        strategy_used=str(turn["strategy_used"]),
                        state_after_turn=dict(turn["state_after_turn"]),
                        generation_notes=turn.get("generation_notes"),
                    )
                )

        latest_snapshot = apply_simulation_job_progress(
            job,
            current_stage="completed",
            current_stage_completed_units=total_units,
            current_stage_total_units=total_units,
            overall_completed_units=total_units,
            overall_total_units=total_units,
            status_message=f"completed {total_units}/{total_units} units",
            status="completed",
            finished_at=_utcnow(),
            error_message=None,
        )
        job.result_simulation_id = simulation.id
        session.commit()
        progress_reporter.maybe_emit(latest_snapshot)
        return True
    except Exception as exc:
        session.rollback()
        if job_id is not None:
            failed_job = session.get(SimulationJob, job_id)
            if failed_job is not None:
                latest_snapshot = apply_simulation_job_progress(
                    failed_job,
                    current_stage="failed",
                    current_stage_completed_units=latest_snapshot.current_stage_completed_units,
                    current_stage_total_units=latest_snapshot.current_stage_total_units,
                    overall_completed_units=latest_snapshot.overall_completed_units,
                    overall_total_units=latest_snapshot.overall_total_units,
                    status_message=f"failed {latest_snapshot.status_message}: {exc}",
                    status="failed",
                    finished_at=_utcnow(),
                    error_message=str(exc),
                )
                session.commit()
                progress_reporter.maybe_emit(latest_snapshot)
        return True
    finally:
        session.close()


def run_forever(*, llm_client, poll_interval_seconds: int = 2) -> None:
    while True:
        processed = run_next_job(llm_client=llm_client, progress_reporter=ConsoleProgressReporter())
        processed = run_next_simulation_job(llm_client=llm_client) or processed
        if not processed:
            time.sleep(poll_interval_seconds)


def _simulation_snapshot_from_job(job: SimulationJob) -> SimulationProgressSnapshot:
    progress = (job.payload_json or {}).get("progress", {})
    current_stage_total_units = int(progress.get("current_stage_total_units", 0) or 0)
    current_stage_completed_units = int(progress.get("current_stage_completed_units", 0) or 0)
    overall_total_units = int(progress.get("overall_total_units", 0) or 0)
    overall_completed_units = int(progress.get("overall_completed_units", 0) or 0)
    return SimulationProgressSnapshot(
        job_id=job.id,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        current_stage_completed_units=current_stage_completed_units,
        current_stage_total_units=current_stage_total_units,
        overall_completed_units=overall_completed_units,
        overall_total_units=overall_total_units,
        status_message=str(progress.get("status_message") or ""),
    )


def _build_simulation_context_pack(
    session,
    *,
    conversation_id: int,
    target_message: Message,
    replacement_content: str,
) -> dict[str, object]:
    messages = (
        session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc(), Message.sequence_no.asc(), Message.id.asc())
        )
        .scalars()
        .all()
    )
    segments = (
        session.execute(
            select(Segment)
            .where(Segment.conversation_id == conversation_id)
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
                RelationshipSnapshot.conversation_id == conversation_id,
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
        conversation_id=conversation_id,
        target_message=target_message,
    )
    personas = (
        session.execute(select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id))
        .scalars()
        .all()
    )
    persona_self = next((item for item in personas if item.subject_role == "self"), None)
    persona_other = next((item for item in personas if item.subject_role == "other"), None)

    return build_context_pack(
        messages=[_simulation_message_to_context_dict(item) for item in messages],
        segments=[_simulation_segment_to_context_dict(item) for item in segments],
        target_message_id=target_message.id,
        replacement_content=replacement_content,
        related_topic_digests=related_topic_digests,
        base_relationship_snapshot=_simulation_snapshot_to_context_dict(snapshot),
        persona_self=_simulation_persona_to_context_dict(persona_self),
        persona_other=_simulation_persona_to_context_dict(persona_other),
    )


def _simulation_message_to_context_dict(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sequence_no": message.sequence_no,
        "timestamp": message.timestamp,
        "speaker_role": message.speaker_role,
        "content_text": message.content_text,
    }


def _simulation_segment_to_context_dict(segment: Segment) -> dict[str, object]:
    return {
        "id": segment.id,
        "source_message_ids": segment.source_message_ids or [],
        "start_time": segment.start_time,
        "end_time": segment.end_time,
    }


def _simulation_snapshot_to_context_dict(snapshot: RelationshipSnapshot | None) -> dict[str, object] | None:
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


def _simulation_persona_to_context_dict(persona: PersonaProfile | None) -> dict[str, object] | None:
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


def _calculate_simulation_total_units(turn_count: int) -> int:
    return max(1, turn_count + 1)


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


def _preview_segments(
    *,
    parsed_messages: list[ParsedMessage],
    gap_minutes: int,
    merge_window_hours: int,
) -> list[SegmentDraft]:
    timeline = [
        ParsedTimelineMessage(index, message.timestamp, message.speaker_role)
        for index, message in enumerate(parsed_messages, start=1)
    ]
    return merge_isolated_segments(
        split_into_segments(timeline, gap_minutes=gap_minutes),
        merge_window_hours=merge_window_hours,
    )


def _materialize_segment_draft(
    preview_segment: SegmentDraft,
    sequence_to_message_id: dict[int, int],
) -> SegmentDraft:
    return SegmentDraft(
        segment_id=preview_segment.segment_id,
        message_ids=[sequence_to_message_id[sequence_no] for sequence_no in preview_segment.message_ids],
        start_time=preview_segment.start_time,
        end_time=preview_segment.end_time,
        self_message_count=preview_segment.self_message_count,
        other_message_count=preview_segment.other_message_count,
        segment_kind=preview_segment.segment_kind,
        source_message_ids=[
            sequence_to_message_id[sequence_no]
            for sequence_no in (preview_segment.source_message_ids or preview_segment.message_ids)
        ],
        source_segment_ids=list(preview_segment.source_segment_ids),
    )


def _calculate_overall_total_units(*, message_count: int, segment_count: int) -> int:
    return message_count + (4 * segment_count) + 3


def _calculate_percent(completed_units: int, total_units: int) -> int:
    if total_units <= 0:
        return 0
    return min(100, int((completed_units * 100) / total_units))


def _performance_elapsed_seconds(performance: dict[str, object] | None) -> float | None:
    if performance is None:
        return None
    elapsed_seconds = performance.get("elapsed_seconds")
    if isinstance(elapsed_seconds, int | float):
        return float(elapsed_seconds)
    return None


def _apply_progress(
    job: AnalysisJob,
    *,
    current_stage: str,
    current_stage_completed_units: int,
    current_stage_total_units: int,
    overall_completed_units: int,
    overall_total_units: int,
    status_message: str,
    status: str | None = None,
    finished_at: datetime | None = None,
    error_message: str | None = None,
    performance: dict[str, object] | None = None,
) -> ProgressSnapshot:
    payload = dict(job.payload_json or {})
    payload["progress"] = {
        "current_stage_total_units": current_stage_total_units,
        "current_stage_completed_units": current_stage_completed_units,
        "overall_total_units": overall_total_units,
        "overall_completed_units": overall_completed_units,
        "status_message": status_message,
    }
    if performance is not None:
        payload["performance"] = performance
    job.payload_json = payload
    job.current_stage = current_stage
    job.progress_percent = _calculate_percent(overall_completed_units, overall_total_units)
    if status is not None:
        job.status = status
    if finished_at is not None:
        job.finished_at = finished_at
    job.error_message = error_message
    return ProgressSnapshot(
        job_id=job.id,
        current_stage=current_stage,
        progress_percent=job.progress_percent,
        current_stage_completed_units=current_stage_completed_units,
        current_stage_total_units=current_stage_total_units,
        overall_completed_units=overall_completed_units,
        overall_total_units=overall_total_units,
        status_message=status_message,
        elapsed_seconds=_performance_elapsed_seconds(performance),
    )


def _segment_summary_payload(summary: SegmentSummary) -> dict:
    return {
        "summary_text": summary.summary_text,
        "main_topics": summary.main_topics,
        "self_stance": summary.self_stance,
        "other_stance": summary.other_stance,
        "emotional_tone": summary.emotional_tone,
        "interaction_pattern": summary.interaction_pattern,
        "has_conflict": summary.has_conflict,
        "has_repair": summary.has_repair,
        "has_closeness_signal": summary.has_closeness_signal,
        "outcome": summary.outcome,
        "relationship_impact": summary.relationship_impact,
        "confidence": summary.confidence,
    }


def _topic_prompt_payload(topic: Topic) -> dict:
    return {
        "topic_id": topic.id,
        "topic_name": topic.topic_name,
        "topic_summary": topic.topic_summary,
        "topic_status": topic.topic_status,
    }


def _normalize_topic_matches(*, matched_topics, existing_topic_ids: set[int]) -> list:
    deduped: dict[int, object] = {}
    for match in matched_topics:
        if match.topic_id not in existing_topic_ids:
            continue
        current = deduped.get(match.topic_id)
        if current is None or match.score > current.score:
            deduped[match.topic_id] = match
    ordered_matches = sorted(deduped.values(), key=lambda item: item.score, reverse=True)
    return ordered_matches[:2]


def _ensure_topic_link(session, *, topic_id: int, segment_id: int, link_reason: str, score: float) -> bool:
    existing = session.execute(
        select(TopicLink).where(TopicLink.topic_id == topic_id, TopicLink.segment_id == segment_id)
    ).scalar_one_or_none()
    if existing is not None:
        if score > existing.score:
            existing.score = score
            existing.link_reason = link_reason
        return False
    session.add(
        TopicLink(
            topic_id=topic_id,
            segment_id=segment_id,
            link_reason=link_reason,
            score=score,
        )
    )
    return True


def _touch_topic_with_segment(topic: Topic, segment: Segment) -> None:
    topic.segment_count += 1
    if segment.start_time < topic.first_seen_at:
        topic.first_seen_at = segment.start_time
    if segment.end_time > topic.last_seen_at:
        topic.last_seen_at = segment.end_time


def _apply_topic_merges(session, *, topics_by_id: dict[int, Topic], merge_decisions) -> dict[int, Topic]:
    claimed_topic_ids: set[int] = set()
    updated_topics = dict(topics_by_id)

    for decision in merge_decisions:
        source_topic_ids = [topic_id for topic_id in decision.source_topic_ids if topic_id in updated_topics]
        if len(source_topic_ids) < 2:
            continue
        if any(topic_id in claimed_topic_ids for topic_id in source_topic_ids):
            continue

        canonical_id = source_topic_ids[0]
        canonical_topic = updated_topics[canonical_id]
        merged_topics = [updated_topics[topic_id] for topic_id in source_topic_ids]
        canonical_topic.topic_name = decision.merged_topic_name
        canonical_topic.topic_summary = decision.merged_topic_summary
        canonical_topic.topic_status = decision.merged_topic_status
        canonical_topic.first_seen_at = min(topic.first_seen_at for topic in merged_topics)
        canonical_topic.last_seen_at = max(topic.last_seen_at for topic in merged_topics)

        for duplicate_id in source_topic_ids[1:]:
            canonical_segment_ids = {
                link.segment_id
                for link in session.execute(
                    select(TopicLink).where(TopicLink.topic_id == canonical_id)
                ).scalars()
            }
            duplicate_links = session.execute(
                select(TopicLink).where(TopicLink.topic_id == duplicate_id)
            ).scalars().all()
            for link in duplicate_links:
                if link.segment_id in canonical_segment_ids:
                    existing_link = session.execute(
                        select(TopicLink).where(
                            TopicLink.topic_id == canonical_id,
                            TopicLink.segment_id == link.segment_id,
                        )
                    ).scalar_one()
                    if link.score > existing_link.score:
                        existing_link.score = link.score
                        existing_link.link_reason = link.link_reason
                    session.delete(link)
                    continue
                link.topic_id = canonical_id
                canonical_segment_ids.add(link.segment_id)

            session.flush()
            session.delete(updated_topics[duplicate_id])
            del updated_topics[duplicate_id]

        canonical_topic.segment_count = len(
            {
                link.segment_id
                for link in session.execute(
                    select(TopicLink).where(TopicLink.topic_id == canonical_id)
                ).scalars()
            }
        )
        claimed_topic_ids.update(source_topic_ids)

    return updated_topics


def _cleanup_failed_job_artifacts(
    *,
    job_id: int,
    conversation_id: int,
    latest_snapshot: ProgressSnapshot,
    error_message: str,
    performance: dict[str, object] | None = None,
) -> None:
    session = get_sessionmaker()()
    try:
        _delete_existing_analysis_artifacts(session, conversation_id=conversation_id)
        job = session.get(AnalysisJob, job_id)
        if job is not None:
            _apply_progress(
                job,
                current_stage="failed",
                current_stage_completed_units=latest_snapshot.current_stage_completed_units,
                current_stage_total_units=latest_snapshot.current_stage_total_units,
                overall_completed_units=latest_snapshot.overall_completed_units,
                overall_total_units=latest_snapshot.overall_total_units,
                status_message=f"failed {latest_snapshot.status_message}: {error_message}",
                status="failed",
                finished_at=_utcnow(),
                error_message=error_message,
                performance=performance,
            )
        conversation = session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.status = "failed"
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
