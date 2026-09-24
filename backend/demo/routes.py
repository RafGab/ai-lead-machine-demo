from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.demo.orchestrator import process_demo_message
from backend.demo.verticals import list_verticals
from backend.demo import repository, booking_service, handoff_service

router = APIRouter(prefix="/demo")


class DemoMessage(BaseModel):
    vertical: str
    message: str = Field(max_length=2000)
    conversation_id: int | None = None
    field: str | None = None
    value: bool | int | float | str | None = None
    source: str = "demo"


class HandoffRequest(BaseModel):
    vertical: str
    conversation_id: int | None = None
    contact: str = Field(default="", max_length=120)
    name: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=500)
    source: str = "demo"


class BookAppointment(BaseModel):
    conversation_id: int
    scheduled_at: str


@router.get("/verticals")
def get_verticals():
    return list_verticals()


@router.post("/message")
def post_message(request: DemoMessage):
    try:
        return process_demo_message(
            vertical=request.vertical,
            message=request.message,
            conversation_id=request.conversation_id,
            field=request.field,
            value=request.value,
            source=request.source,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/handoff")
def request_handoff(request: HandoffRequest):
    try:
        return handoff_service.request_handoff(
            vertical=request.vertical,
            source=request.source,
            conversation_id=request.conversation_id,
            contact=request.contact,
            name=request.name,
            note=request.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/book-appointment")
def book_appointment(request: BookAppointment):
    try:
        return booking_service.schedule_appointment(
            conversation_id=request.conversation_id,
            scheduled_at=request.scheduled_at,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return conversation
