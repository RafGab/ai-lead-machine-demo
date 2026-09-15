import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database.database import get_connection

router = APIRouter()


def _check_admin_key(key: str | None) -> None:
    """
    Protege los listados (contienen datos personales de leads reales)
    para que no sean legibles por cualquiera que encuentre la URL del
    backend en el código fuente de la página pública.
    """

    expected = os.getenv("ADMIN_KEY")

    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Clave de administración inválida.")


class StudyLeadRequest(BaseModel):
    name: str
    email: str
    phone: str | None = None
    nationality: str | None = None
    admission: str | None = None
    city: str | None = None
    start_date: str | None = None
    message: str | None = None


@router.post("/study-leads")
def create_study_lead(request: StudyLeadRequest):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO study_leads
        (name, email, phone, nationality, admission, city, start_date, message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.name,
            request.email,
            request.phone,
            request.nationality,
            request.admission,
            request.city,
            request.start_date,
            request.message,
        ),
    )

    connection.commit()
    connection.close()

    return {"status": "ok"}


@router.get("/study-leads")
def list_study_leads(key: str | None = None):
    _check_admin_key(key)

    connection = get_connection()

    rows = connection.execute(
        "SELECT * FROM study_leads ORDER BY created_at DESC"
    ).fetchall()

    connection.close()

    return [dict(row) for row in rows]
