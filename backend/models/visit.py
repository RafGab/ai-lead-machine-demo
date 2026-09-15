from pydantic import BaseModel


class Visit(BaseModel):
    id: int | None = None
    conversation_id: int | None = None
    property_id: int
    scheduled_at: str
    lead_name: str | None = None
    lead_phone: str | None = None
    lead_email: str | None = None
    calendar_event_id: str | None = None
    calendar_status: str = "not_configured"
    created_at: str | None = None
