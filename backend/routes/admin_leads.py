from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from backend.demo import leads_service
from backend.routes.study_leads import _check_admin_key

router = APIRouter()


class LeadStatusUpdate(BaseModel):
    status: str
    note: str | None = Field(default=None, max_length=500)


def _filters(vertical, scope, status, incomplete):
    if status is not None and status not in leads_service.STATUSES:
        raise HTTPException(status_code=400, detail="Estado no válido.")

    return leads_service.list_leads(
        vertical=vertical or None,
        scope=scope,
        status=status or None,
        include_incomplete=incomplete,
    )


@router.get("/admin/leads")
def list_admin_leads(
    key: str | None = None,
    vertical: str | None = None,
    scope: str = "site",
    status: str | None = None,
    incomplete: bool = False,
):
    _check_admin_key(key)

    return _filters(vertical, scope, status, incomplete)


@router.get("/admin/leads.csv")
def export_admin_leads(
    key: str | None = None,
    vertical: str | None = None,
    scope: str = "site",
    status: str | None = None,
    incomplete: bool = False,
):
    _check_admin_key(key)

    leads = _filters(vertical, scope, status, incomplete)["leads"]

    return Response(
        content=leads_service.leads_to_csv(leads),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


@router.post("/admin/leads/{lead_id}/status")
def update_lead_status(lead_id: str, update: LeadStatusUpdate, key: str | None = None):
    _check_admin_key(key)

    try:
        found = leads_service.set_status(lead_id, update.status, update.note)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    if not found:
        raise HTTPException(status_code=404, detail="Lead no encontrado.")

    return {"status": "ok"}
