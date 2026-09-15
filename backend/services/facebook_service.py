import logging
import os

import httpx

from backend.services.conversation_repository import (
    create_conversation,
    save_message,
    update_lead_data,
)

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"

FIELD_NAME_MAP = {
    "full_name": "name",
    "first_name": "name",
    "email": "email",
    "phone_number": "phone",
}


class FacebookNotConfigured(Exception):
    pass


def _get_page_access_token() -> str:
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

    if not token:
        raise FacebookNotConfigured(
            "FACEBOOK_PAGE_ACCESS_TOKEN no está configurado en el archivo .env."
        )

    return token


def fetch_lead_fields(leadgen_id: str) -> list[dict]:
    """
    Descarga las respuestas del formulario de un lead concreto
    usando el ID recibido en la notificación del webhook.
    """

    access_token = _get_page_access_token()

    response = httpx.get(
        f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
        params={"access_token": access_token, "fields": "field_data"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json().get("field_data", [])


def map_lead_fields(field_data: list[dict]) -> dict:
    """
    Convierte los campos del formulario de Facebook (full_name,
    email, phone_number, y cualquier pregunta personalizada) en
    el formato de lead_data que usa el resto de la aplicación.
    """

    lead_data = {}

    for field in field_data:
        field_name = field.get("name")
        values = field.get("values") or []

        if not field_name or not values:
            continue

        mapped_name = FIELD_NAME_MAP.get(field_name, field_name)
        lead_data[mapped_name] = values[0]

    return lead_data


def process_lead(leadgen_id: str) -> int:
    """
    Descarga los datos de un lead de Facebook Lead Ads y crea una
    conversación con esa información ya precargada, lista para que
    el agente IA continúe la cualificación.

    Devuelve el conversation_id creado.
    """

    field_data = fetch_lead_fields(leadgen_id)
    lead_data = map_lead_fields(field_data)

    conversation_id = create_conversation()

    update_lead_data(conversation_id, lead_data)

    save_message(
        conversation_id,
        "assistant",
        "Hemos recibido tu solicitud desde Facebook. "
        "En breve un agente se pondrá en contacto contigo."
    )

    logger.info(
        "Lead de Facebook %s importado como conversación %s",
        leadgen_id,
        conversation_id,
    )

    return conversation_id
