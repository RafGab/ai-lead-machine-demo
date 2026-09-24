import logging

from backend.demo import repository
from backend.demo.lead_notification import notify_appointment_booked
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services.calendar_service import (
    CalendarNotConfigured,
    create_event,
    is_slot_available,
    suggest_alternative_slots,
)

logger = logging.getLogger(__name__)


def _label_for(vertical: str) -> str:
    module = GENERIC_VERTICALS.get(vertical)
    return module.LABEL if module else vertical


def schedule_appointment(conversation_id: int, scheduled_at: str) -> dict:
    """
    Agenda una cita para una conversación de la demo ya completada: la
    guarda en la base de datos y, si el rubro tiene un calendario de
    Google configurado (propio o el genérico), crea el evento
    correspondiente.
    """

    conversation = repository.get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(f"La conversación {conversation_id} no existe.")

    vertical = conversation["vertical"]
    lead = conversation["lead_data"]

    try:
        available = is_slot_available(scheduled_at, vertical=vertical)
    except CalendarNotConfigured:
        available = None

    if available is False:
        alternatives = suggest_alternative_slots(scheduled_at, vertical=vertical)

        return {
            "appointment_id": None,
            "calendar_status": "unavailable",
            "calendar_event_id": None,
            "message": (
                "Ese horario ya está ocupado. Aquí tienes algunas alternativas cercanas."
            ),
            "alternative_slots": alternatives,
        }

    lead_name = lead.get("name")
    lead_phone = lead.get("phone")
    lead_email = lead.get("email")

    appointment_id = repository.create_appointment(
        conversation_id=conversation_id,
        vertical=vertical,
        scheduled_at=scheduled_at,
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_email=lead_email,
    )

    label = _label_for(vertical)

    description_lines = [
        "Cita generada automáticamente por el agente IA.",
        f"Rubro: {label}",
    ]

    for field_name, field_value in lead.items():
        if field_name in ("name", "phone", "email") or field_value in (None, "", False):
            continue
        description_lines.append(f"{field_name}: {field_value}")

    if lead_phone:
        description_lines.append(f"Teléfono: {lead_phone}")

    calendar_status = "not_configured"
    calendar_event_id = None
    calendar_message = (
        "Tu cita se guardó, pero el calendario todavía no está configurado — "
        "el equipo te confirmará por teléfono."
    )

    try:
        calendar_event_id = create_event(
            summary=f"{label}: {lead_name or 'Nuevo lead'}",
            description="\n".join(description_lines),
            scheduled_at=scheduled_at,
            attendee_email=lead_email,
            vertical=vertical,
        )
        calendar_status = "synced"
        calendar_message = "¡Tu cita quedó agendada y se notificó al equipo!"
    except CalendarNotConfigured:
        logger.info(
            "Cita %s guardada sin sincronizar: calendario no configurado (vertical=%s).",
            appointment_id, vertical,
        )
    except Exception:
        calendar_status = "error"
        calendar_message = (
            "Tu cita se guardó, pero hubo un error al sincronizar con el calendario."
        )
        logger.exception(
            "Fallo al crear el evento de calendario para la cita %s", appointment_id
        )

    repository.set_appointment_calendar_result(
        appointment_id=appointment_id,
        calendar_status=calendar_status,
        calendar_event_id=calendar_event_id,
    )

    try:
        notify_appointment_booked(
            vertical=vertical,
            source=conversation.get("source", "demo"),
            lead=lead,
            scheduled_at=scheduled_at,
            calendar_status=calendar_status,
        )
    except Exception:
        logger.exception("Fallo al avisar de la cita %s", appointment_id)

    return {
        "appointment_id": appointment_id,
        "calendar_status": calendar_status,
        "calendar_event_id": calendar_event_id,
        "message": calendar_message,
        "alternative_slots": [],
    }
