from pydantic import BaseModel


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


class ImportResponse(BaseModel):
    conversation: ConversationRead
    job: JobRead
