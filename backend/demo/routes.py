from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.demo.orchestrator import process_demo_message
from backend.demo.verticals import list_verticals
from backend.demo import repository

router = APIRouter(prefix="/demo")


class DemoMessage(BaseModel):
    vertical: str
    message: str
    conversation_id: int | None = None
    field: str | None = None
    value: bool | int | float | str | None = None


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
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return conversation
