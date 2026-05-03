from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update

from if_then_mvp.models import BranchMessage, BranchReplyJob, BranchSession
from if_then_mvp.schemas import BranchMessageRead, BranchReplyJobRead, BranchSessionRead


ACTIVE_REPLY_JOB_STATUSES = ("queued", "running")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_branch_session(
    session,
    *,
    conversation_id: int,
    target_message_id: int,
    replacement_content: str,
    context_pack: dict,
) -> BranchSession:
    replacement = replacement_content.strip()
    if not replacement:
        raise ValueError("replacement_content must not be empty")

    memory_pack = _build_session_memory_pack(context_pack=context_pack)
    branch_session = BranchSession(
        conversation_id=conversation_id,
        target_message_id=target_message_id,
        replacement_content=replacement,
        context_pack_snapshot=context_pack,
        session_memory_pack=memory_pack,
        current_branch_state=context_pack.get("moment_state_estimate") or {},
        input_revision=1,
        status="active",
    )
    session.add(branch_session)
    session.flush()

    session.add(
        BranchMessage(
            branch_session_id=branch_session.id,
            sequence_no=1,
            speaker_role="self",
            content_text=replacement,
            source="rewrite",
            delivery_state="committed",
            metadata_json={"target_message_id": target_message_id},
        )
    )
    session.flush()
    return branch_session


def append_branch_self_message(
    session,
    *,
    branch_session: BranchSession,
    content_text: str,
) -> BranchMessage:
    content = content_text.strip()
    if not content:
        raise ValueError("content_text must not be empty")
    if branch_session.status != "active":
        raise ValueError("Branch session is not active")

    supersede_active_reply_jobs(
        session,
        branch_session_id=branch_session.id,
        reason="superseded by new self message",
    )
    branch_session.input_revision += 1
    branch_session.updated_at = utcnow()
    message = BranchMessage(
        branch_session_id=branch_session.id,
        sequence_no=_next_branch_message_sequence_no(session, branch_session_id=branch_session.id),
        speaker_role="self",
        content_text=content,
        source="user",
        delivery_state="committed",
        metadata_json={"input_revision": branch_session.input_revision},
    )
    session.add(message)
    session.flush()
    return message


def queue_branch_reply_job(session, *, branch_session: BranchSession) -> BranchReplyJob:
    if branch_session.status != "active":
        raise ValueError("Branch session is not active")

    supersede_active_reply_jobs(
        session,
        branch_session_id=branch_session.id,
        reason="superseded by newer reply job",
    )
    job = BranchReplyJob(
        branch_session_id=branch_session.id,
        status="queued",
        current_stage="queued",
        progress_percent=0,
        input_revision=branch_session.input_revision,
        payload_json={
            "queued_at": utcnow().isoformat(),
            "progress": {
                "status_message": "等待 worker 处理",
                "current_stage_total_units": 1,
                "current_stage_completed_units": 0,
                "overall_total_units": 1,
                "overall_completed_units": 0,
            },
        },
    )
    session.add(job)
    session.flush()
    return job


def supersede_active_reply_jobs(session, *, branch_session_id: int, reason: str) -> None:
    now = utcnow()
    for job in session.execute(
        select(BranchReplyJob).where(
            BranchReplyJob.branch_session_id == branch_session_id,
            BranchReplyJob.status.in_(ACTIVE_REPLY_JOB_STATUSES),
        )
    ).scalars():
        apply_branch_reply_job_progress(
            job,
            current_stage="superseded",
            current_stage_completed_units=0,
            current_stage_total_units=1,
            overall_completed_units=0,
            overall_total_units=1,
            status_message=reason,
            status="superseded",
            finished_at=now,
            error_message=None,
        )


def claim_next_branch_reply_job(session) -> BranchReplyJob | None:
    next_job_id = (
        select(BranchReplyJob.id)
        .where(BranchReplyJob.status == "queued")
        .order_by(BranchReplyJob.id.asc())
        .limit(1)
        .scalar_subquery()
    )
    row = session.execute(
        update(BranchReplyJob)
        .where(BranchReplyJob.id == next_job_id, BranchReplyJob.status == "queued")
        .values(
            status="running",
            current_stage="generating",
            progress_percent=0,
            started_at=utcnow(),
            finished_at=None,
            error_message=None,
        )
        .returning(BranchReplyJob.id)
    ).first()
    if row is None:
        session.rollback()
        return None

    job = session.get(BranchReplyJob, row.id)
    if job is None:
        session.rollback()
        return None

    apply_branch_reply_job_progress(
        job,
        current_stage="generating",
        current_stage_completed_units=0,
        current_stage_total_units=1,
        overall_completed_units=0,
        overall_total_units=1,
        status_message="generating 0/1 reply",
        status="running",
        started_at=job.started_at,
        finished_at=None,
        error_message=None,
    )
    session.commit()
    return job


def apply_branch_reply_job_progress(
    job: BranchReplyJob,
    *,
    current_stage: str,
    current_stage_completed_units: int,
    current_stage_total_units: int,
    overall_completed_units: int,
    overall_total_units: int,
    status_message: str,
    status: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> None:
    payload = dict(job.payload_json or {})
    payload["progress"] = {
        "current_stage_total_units": current_stage_total_units,
        "current_stage_completed_units": current_stage_completed_units,
        "overall_total_units": overall_total_units,
        "overall_completed_units": overall_completed_units,
        "status_message": status_message,
    }
    job.payload_json = payload
    job.current_stage = current_stage
    job.progress_percent = _calculate_percent(overall_completed_units, overall_total_units)
    if status is not None:
        job.status = status
    if started_at is not None:
        job.started_at = started_at
    if finished_at is not None:
        job.finished_at = finished_at
    job.error_message = error_message


def branch_session_to_read(session, branch_session: BranchSession) -> BranchSessionRead:
    messages = (
        session.execute(
            select(BranchMessage)
            .where(BranchMessage.branch_session_id == branch_session.id)
            .order_by(BranchMessage.sequence_no.asc(), BranchMessage.id.asc())
        )
        .scalars()
        .all()
    )
    jobs = (
        session.execute(
            select(BranchReplyJob)
            .where(BranchReplyJob.branch_session_id == branch_session.id)
            .order_by(BranchReplyJob.id.desc())
        )
        .scalars()
        .all()
    )
    return BranchSessionRead(
        id=branch_session.id,
        conversation_id=branch_session.conversation_id,
        target_message_id=branch_session.target_message_id,
        replacement_content=branch_session.replacement_content,
        input_revision=branch_session.input_revision,
        status=branch_session.status,
        current_branch_state=branch_session.current_branch_state,
        messages=[branch_message_to_read(message) for message in messages],
        reply_jobs=[branch_reply_job_to_read(job) for job in jobs],
    )


def branch_message_to_read(message: BranchMessage) -> BranchMessageRead:
    return BranchMessageRead.model_validate(message, from_attributes=True)


def branch_reply_job_to_read(job: BranchReplyJob) -> BranchReplyJobRead:
    progress = (job.payload_json or {}).get("progress", {})
    return BranchReplyJobRead(
        id=job.id,
        branch_session_id=job.branch_session_id,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        input_revision=job.input_revision,
        error_message=job.error_message,
        status_message=progress.get("status_message"),
    )


def _next_branch_message_sequence_no(session, *, branch_session_id: int) -> int:
    current_max = session.execute(
        select(func.max(BranchMessage.sequence_no)).where(BranchMessage.branch_session_id == branch_session_id)
    ).scalar_one()
    return int(current_max or 0) + 1


def _calculate_percent(completed_units: int, total_units: int) -> int:
    if total_units <= 0:
        return 0
    return min(100, int((completed_units * 100) / total_units))


def _build_session_memory_pack(*, context_pack: dict) -> dict:
    return {
        "strategy_version": "realtime-branch-memory-v2",
        "layered_context_pack": {
            "cutoff_safe_facts": context_pack.get("cutoff_safe_facts") or {},
            "future_evidence_digests": context_pack.get("future_evidence_digests") or [],
            "branch_facts": context_pack.get("branch_facts") or {},
            "evidence_policy": context_pack.get("evidence_policy") or {},
        },
        "compatibility": {
            "cutoff_safe_context_pack": context_pack,
        },
        "persona_priority": {
            "primary_generation_target": "persona_other",
            "self_interpretation_context": "persona_self",
        },
    }
