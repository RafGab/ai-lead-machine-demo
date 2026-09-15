from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import visit_repository, visit_service

router = APIRouter()


class ScheduleVisitRequest(BaseModel):
    property_id: int
    scheduled_at: str
    conversation_id: int | None = None
    lead_name: str | None = None
    lead_phone: str | None = None
    lead_email: str | None = None


@router.post("/visits")
def schedule_visit(request: ScheduleVisitRequest):
    try:
        return visit_service.schedule_visit(
            property_id=request.property_id,
            scheduled_at=request.scheduled_at,
            conversation_id=request.conversation_id,
            lead_name=request.lead_name,
            lead_phone=request.lead_phone,
            lead_email=request.lead_email,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/visits")
def list_visits():
    return visit_repository.list_visits()
