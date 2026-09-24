import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import get_connection
from backend.services.notify import send_notification

router = APIRouter()


def _check_admin_key(key: str | None) -> None:
    expected = os.getenv("ADMIN_KEY")

    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Clave de administración inválida.")


class BusinessLeadRequest(BaseModel):
    name: str
    business_name: str | None = None
    email: str
    phone: str | None = None
    vertical_interest: str | None = None
    message: str | None = None


@router.post("/business-leads")
def create_business_lead(request: BusinessLeadRequest):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO business_leads
        (name, business_name, email, phone, vertical_interest, message)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            request.name,
            request.business_name,
            request.email,
            request.phone,
            request.vertical_interest,
            request.message,
        ),
    )

    connection.commit()
    connection.close()

    lines = [
        f"Nombre: {request.name}",
        f"Negocio: {request.business_name or '-'}",
        f"Correo: {request.email}",
        f"Teléfono: {request.phone or '-'}",
        f"Rubro de interés: {request.vertical_interest or '-'}",
        "",
        f"Mensaje: {request.message or '-'}",
    ]
    send_notification(
        f"Nuevo interesado en AI Lead Machine: {request.business_name or request.name}",
        "\n".join(lines),
    )

    return {"status": "ok"}


@router.get("/business-leads")
def list_business_leads(key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    rows = connection.execute(
        "SELECT * FROM business_leads ORDER BY created_at DESC"
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]
