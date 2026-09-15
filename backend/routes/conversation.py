from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import conversation_repository
from backend.services.conversation_service import process_message


router = APIRouter()


class ConversationMessage(BaseModel):
    message: str
    conversation_id: int | None = None
    field: str | None = None
    value: bool | int | float | str | None = None


@router.post("/conversations/message")
def conversation_message(request: ConversationMessage):

    return process_message(
        message=request.message,
        conversation_id=request.conversation_id,
        field=request.field,
        value=request.value
    )


@router.get("/conversations")
def list_conversations():
    return conversation_repository.list_conversations()


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int):
    conversation = conversation_repository.get_conversation(conversation_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")

    return conversation