from pathlib import Path

from sqlalchemy import select

from if_then_mvp.models import (
    AnalysisJob,
    BranchMessage,
    BranchReplyJob,
    BranchSession,
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


def clear_conversation_simulations(session, *, conversation_id: int) -> None:
    clear_conversation_branch_sessions(session, conversation_id=conversation_id)
    for turn in session.execute(
        select(SimulationTurn)
        .join(Simulation, SimulationTurn.simulation_id == Simulation.id)
        .where(Simulation.conversation_id == conversation_id)
    ).scalars():
        session.delete(turn)
    for simulation in session.execute(
        select(Simulation).where(Simulation.conversation_id == conversation_id)
    ).scalars():
        session.delete(simulation)
    session.flush()


def clear_conversation_branch_sessions(session, *, conversation_id: int) -> None:
    for reply_job in session.execute(
        select(BranchReplyJob)
        .join(BranchSession, BranchReplyJob.branch_session_id == BranchSession.id)
        .where(BranchSession.conversation_id == conversation_id)
    ).scalars():
        session.delete(reply_job)
    for branch_message in session.execute(
        select(BranchMessage)
        .join(BranchSession, BranchMessage.branch_session_id == BranchSession.id)
        .where(BranchSession.conversation_id == conversation_id)
    ).scalars():
        session.delete(branch_message)
    for branch_session in session.execute(
        select(BranchSession).where(BranchSession.conversation_id == conversation_id)
    ).scalars():
        session.delete(branch_session)
    session.flush()


def queue_rerun_analysis(session, *, conversation_id: int) -> AnalysisJob:
    active_job = session.execute(
        select(AnalysisJob).where(
            AnalysisJob.conversation_id == conversation_id,
            AnalysisJob.job_type == "full_analysis",
            AnalysisJob.status.in_(("queued", "running")),
        )
    ).scalar_one_or_none()
    if active_job is not None:
        raise ValueError("Analysis already queued or running")

    latest_batch = session.execute(
        select(ImportBatch)
        .where(ImportBatch.conversation_id == conversation_id)
        .order_by(ImportBatch.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_batch is None:
        raise ValueError("Conversation has no import batch")

    clear_conversation_simulations(session, conversation_id=conversation_id)
    retry_stage = _resolve_retry_stage(session, conversation_id=conversation_id)

    conversation = session.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.status = "queued"

    payload_json = {"import_id": latest_batch.id}
    current_stage = "created"
    if retry_stage is not None:
        payload_json["resume_from_stage"] = retry_stage
        current_stage = retry_stage

    job = AnalysisJob(
        conversation_id=conversation_id,
        job_type="full_analysis",
        status="queued",
        current_stage=current_stage,
        progress_percent=0,
        retry_count=0,
        payload_json=payload_json,
    )
    session.add(job)
    session.flush()
    return job


def _resolve_retry_stage(session, *, conversation_id: int) -> str | None:
    failed_job = (
        session.execute(
            select(AnalysisJob)
            .where(
                AnalysisJob.conversation_id == conversation_id,
                AnalysisJob.job_type == "full_analysis",
                AnalysisJob.status == "failed",
            )
            .order_by(AnalysisJob.id.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    if failed_job is None:
        return None

    progress = failed_job.payload_json.get("progress", {}) if isinstance(failed_job.payload_json, dict) else {}
    raw_stages = progress.get("stages", []) if isinstance(progress, dict) else []
    failed_stage_ids = {
        str(stage.get("id"))
        for stage in raw_stages
        if isinstance(stage, dict) and stage.get("status") == "failed"
    }
    failed_in_summarizing = "summarizing" in failed_stage_ids
    failed_in_topic_stage = bool(failed_stage_ids & {"topic_resolution", "persona", "snapshots"})
    if not failed_in_summarizing and not failed_in_topic_stage:
        return None

    segment_count = len(
        session.execute(
            select(Segment.id).where(Segment.conversation_id == conversation_id)
        ).all()
    )
    summary_count = len(
        session.execute(
            select(SegmentSummary.id)
            .join(Segment, SegmentSummary.segment_id == Segment.id)
            .where(Segment.conversation_id == conversation_id)
        ).all()
    )
    if segment_count > 0 and summary_count < segment_count:
        return "summarizing"
    if segment_count > 0 and summary_count == segment_count:
        return "topic_persona_snapshot"
    raise ValueError("Failed stage artifacts are missing; import the chat again to run analysis")


def delete_conversation_tree(session, *, conversation_id: int) -> list[Path]:
    upload_paths = [
        Path(batch.source_file_path)
        for batch in session.execute(
            select(ImportBatch).where(ImportBatch.conversation_id == conversation_id)
        ).scalars()
    ]

    clear_conversation_branch_sessions(session, conversation_id=conversation_id)

    for turn in session.execute(
        select(SimulationTurn)
        .join(Simulation, SimulationTurn.simulation_id == Simulation.id)
        .where(Simulation.conversation_id == conversation_id)
    ).scalars():
        session.delete(turn)
    for simulation_job in session.execute(
        select(SimulationJob).where(SimulationJob.conversation_id == conversation_id)
    ).scalars():
        session.delete(simulation_job)
    for simulation in session.execute(
        select(Simulation).where(Simulation.conversation_id == conversation_id)
    ).scalars():
        session.delete(simulation)
    for snapshot in session.execute(
        select(RelationshipSnapshot).where(RelationshipSnapshot.conversation_id == conversation_id)
    ).scalars():
        session.delete(snapshot)
    for persona in session.execute(
        select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id)
    ).scalars():
        session.delete(persona)
    for topic_link in session.execute(
        select(TopicLink)
        .join(Topic, TopicLink.topic_id == Topic.id)
        .where(Topic.conversation_id == conversation_id)
    ).scalars():
        session.delete(topic_link)
    for topic in session.execute(select(Topic).where(Topic.conversation_id == conversation_id)).scalars():
        session.delete(topic)
    for summary in session.execute(
        select(SegmentSummary)
        .join(Segment, SegmentSummary.segment_id == Segment.id)
        .where(Segment.conversation_id == conversation_id)
    ).scalars():
        session.delete(summary)
    for segment in session.execute(
        select(Segment).where(Segment.conversation_id == conversation_id)
    ).scalars():
        session.delete(segment)
    for message in session.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    ).scalars():
        session.delete(message)
    for job in session.execute(
        select(AnalysisJob).where(AnalysisJob.conversation_id == conversation_id)
    ).scalars():
        session.delete(job)
    for batch in session.execute(
        select(ImportBatch).where(ImportBatch.conversation_id == conversation_id)
    ).scalars():
        session.delete(batch)

    conversation = session.get(Conversation, conversation_id)
    if conversation is not None:
        session.delete(conversation)

    session.flush()
    return upload_paths
