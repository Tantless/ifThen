from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    sql_type: str
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: object = None
    json: bool = False


class Model:
    __tablename__: str
    __pk__: str = "id"
    __fields__: tuple[FieldSpec, ...] = ()

    def __init__(self, **kwargs):
        for field in self.__fields__:
            value = kwargs.pop(field.name, field.default)
            setattr(self, field.name, value)
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return tuple(field.name for field in cls.__fields__)

    @classmethod
    def pk_field(cls) -> FieldSpec:
        for field in cls.__fields__:
            if field.primary_key:
                return field
        raise ValueError(f"{cls.__name__} does not define a primary key")


class Conversation(Model):
    __tablename__ = "conversations"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("title", "TEXT", nullable=False),
        FieldSpec("chat_type", "TEXT", nullable=False),
        FieldSpec("self_display_name", "TEXT", nullable=False),
        FieldSpec("other_display_name", "TEXT", nullable=False),
        FieldSpec("source_format", "TEXT", nullable=False),
        FieldSpec("status", "TEXT", nullable=False, default="queued"),
    )


class ImportBatch(Model):
    __tablename__ = "imports"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("source_file_name", "TEXT", nullable=False),
        FieldSpec("source_file_path", "TEXT", nullable=False),
        FieldSpec("source_file_hash", "TEXT", nullable=False),
        FieldSpec("message_count_hint", "INTEGER"),
    )


class Message(Model):
    __tablename__ = "messages"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("import_id", "INTEGER", nullable=False),
        FieldSpec("sequence_no", "INTEGER", nullable=False),
        FieldSpec("speaker_name", "TEXT", nullable=False),
        FieldSpec("speaker_role", "TEXT", nullable=False),
        FieldSpec("timestamp", "TEXT", nullable=False),
        FieldSpec("content_text", "TEXT", nullable=False),
        FieldSpec("message_type", "TEXT", nullable=False),
        FieldSpec("resource_items", "TEXT", json=True),
        FieldSpec("parse_flags", "TEXT", json=True),
        FieldSpec("raw_block_text", "TEXT"),
        FieldSpec("raw_speaker_label", "TEXT"),
        FieldSpec("source_line_start", "INTEGER"),
        FieldSpec("source_line_end", "INTEGER"),
    )


class Segment(Model):
    __tablename__ = "segments"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("start_message_id", "INTEGER", nullable=False),
        FieldSpec("end_message_id", "INTEGER", nullable=False),
        FieldSpec("start_time", "TEXT", nullable=False),
        FieldSpec("end_time", "TEXT", nullable=False),
        FieldSpec("message_count", "INTEGER", nullable=False),
        FieldSpec("self_message_count", "INTEGER", nullable=False),
        FieldSpec("other_message_count", "INTEGER", nullable=False),
        FieldSpec("segment_kind", "TEXT", nullable=False),
        FieldSpec("source_segment_ids", "TEXT", json=True),
        FieldSpec("source_message_ids", "TEXT", json=True),
    )


class SegmentSummary(Model):
    __tablename__ = "segment_summaries"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("segment_id", "INTEGER", nullable=False, unique=True),
        FieldSpec("summary_text", "TEXT", nullable=False),
        FieldSpec("main_topics", "TEXT", json=True, nullable=False),
        FieldSpec("self_stance", "TEXT", nullable=False),
        FieldSpec("other_stance", "TEXT", nullable=False),
        FieldSpec("emotional_tone", "TEXT", nullable=False),
        FieldSpec("interaction_pattern", "TEXT", nullable=False),
        FieldSpec("has_conflict", "INTEGER", nullable=False, default=False),
        FieldSpec("has_repair", "INTEGER", nullable=False, default=False),
        FieldSpec("has_closeness_signal", "INTEGER", nullable=False, default=False),
        FieldSpec("outcome", "TEXT", nullable=False),
        FieldSpec("relationship_impact", "TEXT", nullable=False),
        FieldSpec("confidence", "REAL", nullable=False),
    )


class Topic(Model):
    __tablename__ = "topics"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("topic_name", "TEXT", nullable=False),
        FieldSpec("topic_summary", "TEXT", nullable=False),
        FieldSpec("first_seen_at", "TEXT", nullable=False),
        FieldSpec("last_seen_at", "TEXT", nullable=False),
        FieldSpec("segment_count", "INTEGER", nullable=False),
        FieldSpec("topic_status", "TEXT", nullable=False),
    )


class TopicLink(Model):
    __tablename__ = "topic_links"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("topic_id", "INTEGER", nullable=False),
        FieldSpec("segment_id", "INTEGER", nullable=False),
        FieldSpec("link_reason", "TEXT", nullable=False),
        FieldSpec("score", "REAL", nullable=False),
    )


class PersonaProfile(Model):
    __tablename__ = "persona_profiles"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("subject_role", "TEXT", nullable=False),
        FieldSpec("global_persona_summary", "TEXT", nullable=False),
        FieldSpec("style_traits", "TEXT", json=True, nullable=False),
        FieldSpec("conflict_traits", "TEXT", json=True, nullable=False),
        FieldSpec("relationship_specific_patterns", "TEXT", json=True, nullable=False),
        FieldSpec("evidence_segment_ids", "TEXT", json=True, nullable=False),
        FieldSpec("confidence", "REAL", nullable=False),
    )


class RelationshipSnapshot(Model):
    __tablename__ = "relationship_snapshots"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("as_of_message_id", "INTEGER", nullable=False),
        FieldSpec("as_of_time", "TEXT", nullable=False),
        FieldSpec("relationship_temperature", "TEXT", nullable=False),
        FieldSpec("tension_level", "TEXT", nullable=False),
        FieldSpec("openness_level", "TEXT", nullable=False),
        FieldSpec("initiative_balance", "TEXT", nullable=False),
        FieldSpec("defensiveness_level", "TEXT", nullable=False),
        FieldSpec("unresolved_conflict_flags", "TEXT", json=True, nullable=False),
        FieldSpec("relationship_phase", "TEXT", nullable=False),
        FieldSpec("snapshot_summary", "TEXT", nullable=False),
    )


class AnalysisJob(Model):
    __tablename__ = "analysis_jobs"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("job_type", "TEXT", nullable=False),
        FieldSpec("status", "TEXT", nullable=False),
        FieldSpec("current_stage", "TEXT", nullable=False),
        FieldSpec("progress_percent", "INTEGER", nullable=False),
        FieldSpec("retry_count", "INTEGER", nullable=False, default=0),
        FieldSpec("error_message", "TEXT"),
        FieldSpec("payload_json", "TEXT", json=True, nullable=False),
        FieldSpec("started_at", "TEXT"),
        FieldSpec("finished_at", "TEXT"),
    )


class Simulation(Model):
    __tablename__ = "simulations"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("conversation_id", "INTEGER", nullable=False),
        FieldSpec("target_message_id", "INTEGER", nullable=False),
        FieldSpec("mode", "TEXT", nullable=False),
        FieldSpec("replacement_content", "TEXT", nullable=False),
        FieldSpec("context_pack_snapshot", "TEXT", json=True),
        FieldSpec("branch_assessment", "TEXT", json=True),
        FieldSpec("first_reply_text", "TEXT"),
        FieldSpec("impact_summary", "TEXT"),
        FieldSpec("status", "TEXT", nullable=False),
        FieldSpec("error_message", "TEXT"),
    )


class SimulationTurn(Model):
    __tablename__ = "simulation_turns"
    __fields__ = (
        FieldSpec("id", "INTEGER", primary_key=True, nullable=False),
        FieldSpec("simulation_id", "INTEGER", nullable=False),
        FieldSpec("turn_index", "INTEGER", nullable=False),
        FieldSpec("speaker_role", "TEXT", nullable=False),
        FieldSpec("message_text", "TEXT", nullable=False),
        FieldSpec("strategy_used", "TEXT", nullable=False),
        FieldSpec("state_after_turn", "TEXT", json=True, nullable=False),
        FieldSpec("generation_notes", "TEXT"),
    )


class AppSetting(Model):
    __tablename__ = "app_settings"
    __pk__ = "setting_key"
    __fields__ = (
        FieldSpec("setting_key", "TEXT", primary_key=True, nullable=False),
        FieldSpec("setting_value", "TEXT", nullable=False),
        FieldSpec("is_secret", "INTEGER", nullable=False, default=False),
        FieldSpec("updated_at", "TEXT"),
    )


MODEL_REGISTRY = [
    Conversation,
    ImportBatch,
    Message,
    Segment,
    SegmentSummary,
    Topic,
    TopicLink,
    PersonaProfile,
    RelationshipSnapshot,
    AnalysisJob,
    Simulation,
    SimulationTurn,
    AppSetting,
]
