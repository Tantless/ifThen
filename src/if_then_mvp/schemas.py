from pydantic import BaseModel, Field


class ConversationRead(BaseModel):
    id: int
    title: str
    chat_type: str
    self_display_name: str
    other_display_name: str
    source_format: str
    status: str


class JobRead(BaseModel):
    id: int
    status: str
    current_stage: str
    progress_percent: int
    current_stage_percent: int = 0
    current_stage_total_units: int = 0
    current_stage_completed_units: int = 0
    overall_total_units: int = 0
    overall_completed_units: int = 0
    status_message: str | None = None


class MessageRead(BaseModel):
    id: int
    sequence_no: int
    speaker_name: str
    speaker_role: str
    timestamp: str
    content_text: str
    message_type: str
    resource_items: list[dict] | None = None


class SegmentRead(BaseModel):
    id: int
    start_message_id: int
    end_message_id: int
    start_time: str
    end_time: str
    message_count: int
    segment_kind: str


class TopicRead(BaseModel):
    id: int
    topic_name: str
    topic_summary: str
    topic_status: str


class SnapshotRead(BaseModel):
    id: int
    as_of_message_id: int
    as_of_time: str
    relationship_temperature: str
    tension_level: str
    openness_level: str
    initiative_balance: str
    defensiveness_level: str
    unresolved_conflict_flags: list[str]
    relationship_phase: str
    snapshot_summary: str


class PersonaProfileRead(BaseModel):
    subject_role: str
    global_persona_summary: str
    style_traits: list[str]
    conflict_traits: list[str]
    relationship_specific_patterns: list[str]
    confidence: float


class SettingRead(BaseModel):
    setting_key: str
    setting_value: str
    is_secret: bool


class SettingWrite(BaseModel):
    setting_key: str
    setting_value: str
    is_secret: bool = False


class ImportResponse(BaseModel):
    conversation: ConversationRead
    job: JobRead


class SimulationCreate(BaseModel):
    conversation_id: int
    target_message_id: int
    replacement_content: str
    mode: str = Field(pattern="^(single_reply|short_thread)$")
    turn_count: int = Field(default=4, ge=0, le=8)


class SimulationTurnRead(BaseModel):
    turn_index: int
    speaker_role: str
    message_text: str
    strategy_used: str
    state_after_turn: dict
    generation_notes: str | None = None


class SimulationRead(BaseModel):
    id: int
    mode: str
    replacement_content: str
    first_reply_text: str | None = None
    impact_summary: str | None = None
    simulated_turns: list[SimulationTurnRead] = Field(default_factory=list)
