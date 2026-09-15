import logging

from backend.database.database import get_connection
from backend.services import visit_repository
from backend.services.calendar_service import (
    CalendarNotConfigured,
    create_visit_event,
    is_slot_available,
    suggest_alternative_slots,
)

logger = logging.getLogger(__name__)


def _get_property(property_id: int) -> dict | None:
    connection = get_connection()

    row = connection.execute(
        "SELECT * FROM properties WHERE id = ?",
        (property_id,),
    ).fetchone()

    connection.close()

    return dict(row) if row else None


def schedule_visit(
    property_id: int,
    scheduled_at: str,
    conversation_id: int | None = None,
    lead_name: str | None = None,
    lead_phone: str | None = None,
    lead_email: str | None = None,
) -> dict:
    """
    Agenda una visita: la guarda en la base de datos y, si el
    calendario del comercial está configurado, crea el evento
    correspondiente en Google Calendar.
    """

    property_data = _get_property(property_id)

    if property_data is None:
        raise ValueError(f"La propiedad {property_id} no existe.")

    try:
        available = is_slot_available(scheduled_at)
    except CalendarNotConfigured:
        available = None

    if available is False:
        alternatives = suggest_alternative_slots(scheduled_at)

        return {
            "visit_id": None,
            "calendar_status": "unavailable",
            "calendar_event_id": None,
            "message": (
                "Esa fecha y hora ya están ocupadas para el comercial. "
                "Aquí tienes algunas alternativas cercanas."
            ),
            "alternative_slots": alternatives,
        }

    visit_id = visit_repository.create_visit(
        property_id=property_id,
        scheduled_at=scheduled_at,
        conversation_id=conversation_id,
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_email=lead_email,
    )

    calendar_status = "not_configured"
    calendar_event_id = None
    calendar_message = (
        "La visita se guardó, pero el calendario del comercial "
        "todavía no está configurado."
    )

    try:
        calendar_event_id = create_visit_event(
            property_title=property_data["title"],
            property_city=property_data["city"],
            scheduled_at=scheduled_at,
            lead_name=lead_name,
            lead_phone=lead_phone,
            lead_email=lead_email,
        )
        calendar_status = "synced"
        calendar_message = "La visita se agendó y se notificó al comercial."
    except CalendarNotConfigured:
        logger.info(
            "Visita %s guardada sin sincronizar: calendario no configurado.",
            visit_id,
        )
    except Exception:
        calendar_status = "error"
        calendar_message = (
            "La visita se guardó, pero hubo un error al sincronizar "
            "con el calendario del comercial."
        )
        logger.exception(
            "Fallo al crear el evento de calendario para la visita %s",
            visit_id,
        )

    visit_repository.set_visit_calendar_result(
        visit_id=visit_id,
        calendar_status=calendar_status,
        calendar_event_id=calendar_event_id,
    )

    return {
        "visit_id": visit_id,
        "calendar_status": calendar_status,
        "calendar_event_id": calendar_event_id,
        "message": calendar_message,
        "alternative_slots": [],
    }
