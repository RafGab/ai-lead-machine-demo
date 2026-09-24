import os

from backend.demo.field_labels import FIELD_LABELS, PII_FIELDS
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services.notify import notify_email_for, send_notification


def _should_notify(source: str) -> bool:
    """
    Los leads que llegan desde la web real de un cliente ("widget") siempre
    avisan. Las pruebas dentro de la demo solo avisan si se activa
    NOTIFY_DEMO_LEADS, para no llenar el correo mientras se prueba.
    """

    if source == "widget":
        return True

    return os.getenv("NOTIFY_DEMO_LEADS", "").lower() in ("1", "true", "yes")


def _label_for(vertical: str) -> str:
    module = GENERIC_VERTICALS.get(vertical)
    return module.LABEL if module else vertical


def _format_lead(lead: dict) -> list[str]:
    lines = []

    contact = [
        ("Nombre", lead.get("name")),
        ("Teléfono", lead.get("phone")),
        ("Correo", lead.get("email")),
    ]

    for label, value in contact:
        if value:
            lines.append(f"{label}: {value}")

    details = [
        f"{FIELD_LABELS.get(field, field)}: {value}"
        for field, value in lead.items()
        if field not in PII_FIELDS and value not in (None, "", False)
    ]

    if details:
        lines.append("")
        lines.extend(details)

    return lines


def notify_lead_completed(
    vertical: str, source: str, lead: dict, priority: str, notes: list[str] | None
) -> None:
    if not _should_notify(source):
        return

    label = _label_for(vertical)
    name = lead.get("name") or "sin nombre"
    urgent = priority not in (None, "normal")

    lines = [f"Un visitante completó la conversación con el asistente de {label}.", ""]
    lines.extend(_format_lead(lead))

    if urgent:
        lines.extend(["", f"Prioridad: {priority}"])

    if notes:
        lines.extend(["", "Notas para el equipo:"])
        lines.extend(f"• {note}" for note in notes)

    lines.extend(["", "Contáctalo pronto: cuanto antes respondas, más probabilidades de cerrar."])

    subject = f"{'[URGENTE] ' if urgent else ''}Nuevo lead de {label}: {name}"
    send_notification(subject, "\n".join(lines), to=notify_email_for(vertical))


def notify_appointment_booked(
    vertical: str, source: str, lead: dict, scheduled_at: str, calendar_status: str
) -> None:
    if not _should_notify(source):
        return

    label = _label_for(vertical)
    name = lead.get("name") or "sin nombre"

    lines = [f"{name} solicitó una cita con {label} para: {scheduled_at}", ""]
    lines.extend(_format_lead(lead))

    if calendar_status != "synced":
        lines.extend([
            "",
            "Ojo: la cita NO se añadió a tu Google Calendar "
            f"(estado: {calendar_status}). Confírmala tú con la persona.",
        ])

    send_notification(
        f"Cita solicitada en {label}: {name} ({scheduled_at})",
        "\n".join(lines),
        to=notify_email_for(vertical),
    )
