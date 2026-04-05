from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False)
    self_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    other_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")

    imports: Mapped[list[ImportBatch]] = relationship(back_populates="conversation")
    jobs: Mapped[list[AnalysisJob]] = relationship(back_populates="conversation")


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    source_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_file_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    message_count_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="imports")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"), index=True, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(255), nullable=False)
    speaker_role: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_items: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    parse_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_block_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_speaker_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Segment(TimestampMixin, Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    start_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    end_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=False)
    start_time: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    end_time: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    self_message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    other_message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_segment_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    source_message_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)


class SegmentSummary(TimestampMixin, Base):
    __tablename__ = "segment_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), unique=True, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    main_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    self_stance: Mapped[str] = mapped_column(Text, nullable=False)
    other_stance: Mapped[str] = mapped_column(Text, nullable=False)
    emotional_tone: Mapped[str] = mapped_column(String(128), nullable=False)
    interaction_pattern: Mapped[str] = mapped_column(String(128), nullable=False)
    has_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_repair: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_closeness_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship_impact: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    topic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[str] = mapped_column(String(32), nullable=False)
    last_seen_at: Mapped[str] = mapped_column(String(32), nullable=False)
    segment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_status: Mapped[str] = mapped_column(String(64), nullable=False)


class TopicLink(TimestampMixin, Base):
    __tablename__ = "topic_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True, nullable=False)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), index=True, nullable=False)
    link_reason: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)


class PersonaProfile(TimestampMixin, Base):
    __tablename__ = "persona_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    subject_role: Mapped[str] = mapped_column(String(32), nullable=False)
    global_persona_summary: Mapped[str] = mapped_column(Text, nullable=False)
    style_traits: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    conflict_traits: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    relationship_specific_patterns: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_segment_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class RelationshipSnapshot(TimestampMixin, Base):
    __tablename__ = "relationship_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    as_of_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True, nullable=False)
    as_of_time: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    relationship_temperature: Mapped[str] = mapped_column(String(64), nullable=False)
    tension_level: Mapped[str] = mapped_column(String(64), nullable=False)
    openness_level: Mapped[str] = mapped_column(String(64), nullable=False)
    initiative_balance: Mapped[str] = mapped_column(String(64), nullable=False)
    defensiveness_level: Mapped[str] = mapped_column(String(64), nullable=False)
    unresolved_conflict_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    relationship_phase: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_summary: Mapped[str] = mapped_column(Text, nullable=False)


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="jobs")


class Simulation(TimestampMixin, Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    target_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    replacement_content: Mapped[str] = mapped_column(Text, nullable=False)
    context_pack_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branch_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    first_reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimulationTurn(TimestampMixin, Base):
    __tablename__ = "simulation_turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"), index=True, nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_used: Mapped[str] = mapped_column(String(128), nullable=False)
    state_after_turn: Mapped[dict] = mapped_column(JSON, nullable=False)
    generation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    setting_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
