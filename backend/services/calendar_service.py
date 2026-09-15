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
