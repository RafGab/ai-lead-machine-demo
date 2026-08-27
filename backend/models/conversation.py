from pydantic import BaseModel


class Conversation(BaseModel):
    id: int | None = None
    lead_data: dict = {}
    created_at: str | None = None
    updated_at: str | None = None


class Message(BaseModel):
    id: int | None = None
    conversation_id: int
    role: str
    content: str
    created_at: str | None = None
    