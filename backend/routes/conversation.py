from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.conversation_service import process_message


router = APIRouter()


class ConversationMessage(BaseModel):
    message: str
    conversation_id: int | None = None


@router.post("/conversations/message")
def conversation_message(request: ConversationMessage):

    return process_message(
        message=request.message,
        conversation_id=request.conversation_id
    )