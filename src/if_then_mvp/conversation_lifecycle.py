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
