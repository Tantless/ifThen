from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, update

from if_then_mvp.models import SimulationJob
from if_then_mvp.schemas import SimulationJobRead


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class SimulationProgressSnapshot:
    job_id: int
    current_stage: str
    progress_percent: int
    current_stage_completed_units: int
    current_stage_total_units: int
    overall_completed_units: int
    overall_total_units: int
    status_message: str


def queue_simulation_job(
    session,
    *,
    conversation_id: int,
    target_message_id: int,
    mode: str,
    turn_count: int,
    replacement_content: str,
) -> SimulationJob:
    job = SimulationJob(
        conversation_id=conversation_id,
        target_message_id=target_message_id,
        mode=mode,
        turn_count=turn_count,
        replacement_content=replacement_content,
        status="queued",
        current_stage="queued",
        progress_percent=0,
        payload_json={
            "queued_at": utcnow().isoformat(),
            "progress": {
                "status_message": "等待 worker 处理",
                "current_stage_total_units": 0,
                "current_stage_completed_units": 0,
                "overall_total_units": 0,
                "overall_completed_units": 0,
            },
        },
    )
    session.add(job)
    session.flush()
    return job


def claim_next_simulation_job(session) -> SimulationJob | None:
    next_job_id = (
        select(SimulationJob.id)
        .where(SimulationJob.status == "queued")
        .order_by(SimulationJob.id.asc())
        .limit(1)
        .scalar_subquery()
    )
    row = session.execute(
        update(SimulationJob)
        .where(SimulationJob.id == next_job_id, SimulationJob.status == "queued")
        .values(
            status="running",
            current_stage="branch_assessment",
            progress_percent=0,
            started_at=utcnow(),
            finished_at=None,
            error_message=None,
        )
        .returning(SimulationJob.id)
    ).first()
    if row is None:
        session.rollback()
        return None

    job = session.get(SimulationJob, row.id)
    if job is None:
        session.rollback()
        return None

    apply_simulation_job_progress(
        job,
        current_stage="branch_assessment",
        current_stage_completed_units=0,
        current_stage_total_units=1,
        overall_completed_units=0,
        overall_total_units=_calculate_overall_total_units(job.turn_count),
        status_message="branch_assessment 0/1 step",
        status="running",
        started_at=job.started_at,
        finished_at=None,
        error_message=None,
    )
    session.commit()
    return job


def apply_simulation_job_progress(
    job: SimulationJob,
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
) -> SimulationProgressSnapshot:
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
    return SimulationProgressSnapshot(
        job_id=job.id,
        current_stage=current_stage,
        progress_percent=job.progress_percent,
        current_stage_completed_units=current_stage_completed_units,
        current_stage_total_units=current_stage_total_units,
        overall_completed_units=overall_completed_units,
        overall_total_units=overall_total_units,
        status_message=status_message,
    )


def simulation_job_to_read(job: SimulationJob) -> SimulationJobRead:
    progress = (job.payload_json or {}).get("progress", {})
    current_stage_total_units = int(progress.get("current_stage_total_units", 0) or 0)
    current_stage_completed_units = int(progress.get("current_stage_completed_units", 0) or 0)
    overall_total_units = int(progress.get("overall_total_units", 0) or 0)
    overall_completed_units = int(progress.get("overall_completed_units", 0) or 0)

    return SimulationJobRead(
        id=job.id,
        conversation_id=job.conversation_id,
        target_message_id=job.target_message_id,
        mode=job.mode,
        turn_count=job.turn_count,
        replacement_content=job.replacement_content,
        status=job.status,
        current_stage=job.current_stage,
        progress_percent=job.progress_percent,
        current_stage_percent=_calculate_percent(current_stage_completed_units, current_stage_total_units),
        current_stage_total_units=current_stage_total_units,
        current_stage_completed_units=current_stage_completed_units,
        overall_total_units=overall_total_units,
        overall_completed_units=overall_completed_units,
        status_message=progress.get("status_message"),
        result_simulation_id=job.result_simulation_id,
        error_message=job.error_message,
    )


def list_simulation_jobs_for_conversation(
    session,
    *,
    conversation_id: int,
    limit: int,
) -> list[SimulationJob]:
    return (
        session.execute(
            select(SimulationJob)
            .where(SimulationJob.conversation_id == conversation_id)
            .order_by(SimulationJob.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )


def _calculate_percent(completed_units: int, total_units: int) -> int:
    if total_units <= 0:
        return 0
    return min(100, int((completed_units * 100) / total_units))


def _calculate_overall_total_units(turn_count: int) -> int:
    return max(1, turn_count + 1)
