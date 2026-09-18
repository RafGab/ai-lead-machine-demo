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


def _calendar_id_for(vertical: str | None) -> str | None:
    """
    Cada rubro puede tener su propio calendario (GOOGLE_CALENDAR_ID_<RUBRO>,
    ej. GOOGLE_CALENDAR_ID_EXTRANJERIA para Acero Pulido), compartido con
    la misma cuenta de servicio. Si no hay uno específico, se usa el
    calendario genérico GOOGLE_CALENDAR_ID (el de inmobiliaria/demo).
    """

    if vertical:
        specific = os.getenv(f"GOOGLE_CALENDAR_ID_{vertical.upper()}")
        if specific:
            return specific

    return os.getenv("GOOGLE_CALENDAR_ID")


def _comercial_email_for(vertical: str | None) -> str | None:
    if vertical:
        specific = os.getenv(f"COMERCIAL_EMAIL_{vertical.upper()}")
        if specific:
            return specific

    return os.getenv("COMERCIAL_EMAIL")


def _calendar_not_configured_message(vertical: str | None) -> str:
    if vertical:
        return (
            f"No hay calendario configurado para \"{vertical}\" "
            f"(GOOGLE_CALENDAR_ID_{vertical.upper()} o GOOGLE_CALENDAR_ID)."
        )

    return "GOOGLE_CALENDAR_ID no está configurado en el archivo .env."


def _post_calendar_event(
    calendar_id: str,
    summary: str,
    description: str,
    scheduled_at: str,
    attendees: list[dict],
) -> str:
    access_token = _get_access_token()
    time_zone = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Madrid")

    start_dt = datetime.fromisoformat(scheduled_at)
    end_dt = start_dt + VISIT_DURATION

    event_body = {
        "summary": summary,
        "description": description,
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

    calendar_id = _calendar_id_for(None)
    comercial_email = _comercial_email_for(None)

    if not calendar_id:
        raise CalendarNotConfigured(
            "GOOGLE_CALENDAR_ID no está configurado en el archivo .env."
        )

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

    return _post_calendar_event(
        calendar_id,
        summary=f"Visita: {property_title}",
        description="\n".join(description_lines),
        scheduled_at=scheduled_at,
        attendees=attendees,
    )


def create_event(
    summary: str,
    description: str,
    scheduled_at: str,
    attendee_email: str | None = None,
    vertical: str | None = None,
) -> str:
    """
    Crea un evento de calendario genérico (cita, consulta...) para
    cualquier rubro de la demo. Igual que create_visit_event pero sin
    atarse al modelo de "propiedad" de inmobiliaria.
    """

    calendar_id = _calendar_id_for(vertical)

    if not calendar_id:
        raise CalendarNotConfigured(_calendar_not_configured_message(vertical))

    attendees = []

    comercial_email = _comercial_email_for(vertical)
    if comercial_email:
        attendees.append({"email": comercial_email})

    if attendee_email:
        attendees.append({"email": attendee_email})

    return _post_calendar_event(
        calendar_id,
        summary=summary,
        description=description,
        scheduled_at=scheduled_at,
        attendees=attendees,
    )


def _parse_business_days(raw: str) -> set[int]:
    return {int(day.strip()) for day in raw.split(",") if day.strip() != ""}


# Horario y días de atención, configurables por cliente vía variables de
# entorno (para no tocar código al adaptar el agente a cada negocio):
#   BUSINESS_HOURS_START / BUSINESS_HOURS_END: hora de inicio/fin (0-23)
#   BUSINESS_DAYS: días de la semana como enteros separados por coma,
#     Monday=0 ... Sunday=6 (por defecto "0,1,2,3,4" = lunes a viernes)
# Cada rubro puede tener su propia franja (ej. BUSINESS_HOURS_START_EXTRANJERIA)
# igual que su propio calendario; si no la define, usa la genérica.
BUSINESS_HOURS_START = int(os.getenv("BUSINESS_HOURS_START", "10"))
BUSINESS_HOURS_END = int(os.getenv("BUSINESS_HOURS_END", "19"))
BUSINESS_DAYS = _parse_business_days(os.getenv("BUSINESS_DAYS", "0,1,2,3,4"))
SLOT_STEP = timedelta(minutes=30)
SEARCH_WINDOW = timedelta(days=5)


def _business_hours_for(vertical: str | None) -> tuple[int, int, set[int]]:
    suffix = f"_{vertical.upper()}" if vertical else ""

    start = int(os.getenv(f"BUSINESS_HOURS_START{suffix}", "") or BUSINESS_HOURS_START)
    end = int(os.getenv(f"BUSINESS_HOURS_END{suffix}", "") or BUSINESS_HOURS_END)
    days_raw = os.getenv(f"BUSINESS_DAYS{suffix}", "")
    days = _parse_business_days(days_raw) if days_raw else BUSINESS_DAYS

    return start, end, days


def _within_business_hours(moment: datetime, vertical: str | None = None) -> bool:
    start, end, days = _business_hours_for(vertical)
    return moment.weekday() in days and start <= moment.hour < end


def _get_busy_periods(
    window_start: datetime, window_end: datetime, vertical: str | None = None
) -> list[tuple[datetime, datetime]]:
    calendar_id = _calendar_id_for(vertical)

    if not calendar_id:
        raise CalendarNotConfigured(_calendar_not_configured_message(vertical))

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


def is_slot_available(scheduled_at: str, vertical: str | None = None) -> bool:
    """
    Comprueba si el horario solicitado cae dentro de la franja de
    atención configurada y si el comercial está libre en ese momento.

    Lanza CalendarNotConfigured si el calendario no está configurado
    (en ese caso no se puede saber la disponibilidad de antemano).
    """

    start_dt = datetime.fromisoformat(scheduled_at)
    end_dt = start_dt + VISIT_DURATION

    # Se consulta el calendario primero: si no está configurado, esto
    # lanza CalendarNotConfigured igual que antes (sin este cambio),
    # así que el resto del flujo no se ve afectado cuando no hay
    # credenciales de Google Calendar todavía.
    busy_periods = _get_busy_periods(start_dt, end_dt, vertical)

    if not _within_business_hours(start_dt, vertical):
        return False

    return not _overlaps(start_dt, end_dt, busy_periods)


def suggest_alternative_slots(
    scheduled_at: str, count: int = 3, vertical: str | None = None
) -> list[str]:
    """
    Busca huecos libres cercanos a la fecha solicitada, dentro del
    horario comercial, para ofrecerlos como alternativa al cliente.
    """

    hours_start, hours_end, days = _business_hours_for(vertical)

    requested_dt = datetime.fromisoformat(scheduled_at)

    window_start = requested_dt.replace(
        hour=hours_start, minute=0, second=0, microsecond=0
    )
    window_end = window_start + SEARCH_WINDOW

    busy_periods = _get_busy_periods(window_start, window_end, vertical)

    suggestions = []
    cursor = window_start

    while cursor < window_end and len(suggestions) < count:
        if cursor.weekday() not in days or cursor.hour >= hours_end:
            cursor = (cursor + timedelta(days=1)).replace(
                hour=hours_start, minute=0
            )
            continue

        slot_end = cursor + VISIT_DURATION

        if cursor != requested_dt and not _overlaps(cursor, slot_end, busy_periods):
            suggestions.append(cursor.isoformat())

        cursor += SLOT_STEP

    return suggestions
