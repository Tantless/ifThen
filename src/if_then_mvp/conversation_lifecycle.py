from pathlib import Path

from sqlalchemy import select

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
    SimulationTurn,
    Topic,
    TopicLink,
)


def clear_conversation_simulations(session, *, conversation_id: int) -> None:
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

    conversation = session.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.status = "queued"

    job = AnalysisJob(
        conversation_id=conversation_id,
        job_type="full_analysis",
        status="queued",
        current_stage="created",
        progress_percent=0,
        retry_count=0,
        payload_json={"import_id": latest_batch.id},
    )
    session.add(job)
    session.flush()
    return job


def delete_conversation_tree(session, *, conversation_id: int) -> list[Path]:
    upload_paths = [
        Path(batch.source_file_path)
        for batch in session.execute(
            select(ImportBatch).where(ImportBatch.conversation_id == conversation_id)
        ).scalars()
    ]

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
