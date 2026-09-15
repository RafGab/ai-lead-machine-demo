import os
from datetime import datetime, timedelta

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
VISIT_DURATION = timedelta(minutes=30)


class CalendarNotConfigured(Exception):
    pass


def _get_access_token() -> str:
    """
    Obtiene un token de acceso usando una cuenta de servicio de Google.

    Requiere la variable de entorno GOOGLE_SERVICE_ACCOUNT_FILE apuntando
    al JSON de credenciales, con el calendario del comercial compartido
    con el email de esa cuenta de servicio (permiso "Realizar cambios en
    los eventos").
    """

    key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if not key_path or not os.path.exists(key_path):
        raise CalendarNotConfigured(
            "GOOGLE_SERVICE_ACCOUNT_FILE no está configurado o el archivo no existe."
        )

    credentials = service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )
    credentials.refresh(GoogleAuthRequest())

    return credentials.token


def create_visit_event(
    property_title: str,
    property_city: str,
    scheduled_at: str,
    lead_name: str | None,
    lead_phone: str | None,
    lead_email: str | None,
) -> str:
    """
    Crea un evento en el calendario del comercial para la visita.

    Devuelve el ID del evento creado en Google Calendar.
    Lanza CalendarNotConfigured si faltan variables de entorno.
    """

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
    comercial_email = os.getenv("COMERCIAL_EMAIL")

    if not calendar_id:
        raise CalendarNotConfigured(
            "GOOGLE_CALENDAR_ID no está configurado en el archivo .env."
        )

    access_token = _get_access_token()

    time_zone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Madrid")

    start_dt = datetime.fromisoformat(scheduled_at)
    end_dt = start_dt + VISIT_DURATION

    description_lines = [
        "Visita generada automáticamente por el agente IA.",
        f"Propiedad: {property_title} ({property_city})",
    ]

    if lead_name:
        description_lines.append(f"Nombre: {lead_name}")

    if lead_phone:
        description_lines.append(f"Teléfono: {lead_phone}")

    if lead_email:
        description_lines.append(f"Email: {lead_email}")

    attendees = []

    if comercial_email:
        attendees.append({"email": comercial_email})

    if lead_email:
        attendees.append({"email": lead_email})

    event_body = {
        "summary": f"Visita: {property_title}",
        "description": "\n".join(description_lines),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": time_zone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": time_zone},
        "attendees": attendees,
    }

    response = httpx.post(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"sendUpdates": "all"},
        json=event_body,
        timeout=10,
    )
    response.raise_for_status()

    return response.json()["id"]


BUSINESS_HOURS_START = 10
BUSINESS_HOURS_END = 19
SLOT_STEP = timedelta(minutes=30)
SEARCH_WINDOW = timedelta(days=5)


def _get_busy_periods(
    window_start: datetime, window_end: datetime
) -> list[tuple[datetime, datetime]]:
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")

    if not calendar_id:
        raise CalendarNotConfigured(
            "GOOGLE_CALENDAR_ID no está configurado en el archivo .env."
        )

    access_token = _get_access_token()

    response = httpx.post(
        "https://www.googleapis.com/calendar/v3/freeBusy",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "timeMin": window_start.isoformat(),
            "timeMax": window_end.isoformat(),
            "items": [{"id": calendar_id}],
        },
        timeout=10,
    )
    response.raise_for_status()

    busy_data = response.json()["calendars"][calendar_id].get("busy", [])

    return [
        (
            datetime.fromisoformat(period["start"]),
            datetime.fromisoformat(period["end"]),
        )
        for period in busy_data
    ]


def _overlaps(
    start: datetime,
    end: datetime,
    busy_periods: list[tuple[datetime, datetime]],
) -> bool:
    return any(
        start < busy_end and end > busy_start
        for busy_start, busy_end in busy_periods
    )


def is_slot_available(scheduled_at: str) -> bool:
    """
    Comprueba si el comercial está libre en la franja solicitada.

    Lanza CalendarNotConfigured si el calendario no está configurado
    (en ese caso no se puede saber la disponibilidad de antemano).
    """

    start_dt = datetime.fromisoformat(scheduled_at)
    end_dt = start_dt + VISIT_DURATION

    busy_periods = _get_busy_periods(start_dt, end_dt)

    return not _overlaps(start_dt, end_dt, busy_periods)


def suggest_alternative_slots(scheduled_at: str, count: int = 3) -> list[str]:
    """
    Busca huecos libres cercanos a la fecha solicitada, dentro del
    horario comercial, para ofrecerlos como alternativa al cliente.
    """

    requested_dt = datetime.fromisoformat(scheduled_at)

    window_start = requested_dt.replace(
        hour=BUSINESS_HOURS_START, minute=0, second=0, microsecond=0
    )
    window_end = window_start + SEARCH_WINDOW

    busy_periods = _get_busy_periods(window_start, window_end)

    suggestions = []
    cursor = window_start

    while cursor < window_end and len(suggestions) < count:
        if cursor.hour >= BUSINESS_HOURS_END:
            cursor = (cursor + timedelta(days=1)).replace(
                hour=BUSINESS_HOURS_START, minute=0
            )
            continue

        slot_end = cursor + VISIT_DURATION

        if cursor != requested_dt and not _overlaps(cursor, slot_end, busy_periods):
            suggestions.append(cursor.isoformat())

        cursor += SLOT_STEP

    return suggestions
