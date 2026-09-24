import re

from backend.demo import repository
from backend.demo.lead_notification import notify_handoff_requested
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services import conversation_repository
from backend.services.sanitize import is_valid_email, is_valid_phone

PHONE_CHARS = re.compile(r"^[\d\s+().\-]+$")
TRANSCRIPT_LIMIT = 8

INVALID_CONTACT_MESSAGE = (
    "Escribe un teléfono válido (con prefijo, por ejemplo +34 600 123 456) o un correo válido."
)


def _load_conversation(vertical: str, conversation_id: int | None) -> dict | None:
    """Lead y últimos mensajes de la conversación, sea de un rubro demo o de inmobiliaria."""

    if conversation_id is None:
        return None

    if vertical == "inmobiliaria":
        conversation = conversation_repository.get_conversation(conversation_id)
    else:
        conversation = repository.get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(f"La conversación {conversation_id} no existe.")

    return conversation


def _classify_contact(contact: str) -> str | None:
    if is_valid_email(contact):
        return "email"

    if PHONE_CHARS.match(contact) and is_valid_phone(contact):
        return "phone"

    return None


def request_handoff(
    vertical: str,
    source: str,
    conversation_id: int | None,
    contact: str,
    name: str,
    note: str,
) -> dict:
    """
    Registra que un visitante quiere hablar con una persona y avisa al
    equipo con prioridad. Si no escribe contacto pero ya lo había dado en
    la conversación, se usa ese.
    """

    if vertical != "inmobiliaria" and vertical not in GENERIC_VERTICALS:
        raise ValueError(f"Rubro de demo desconocido: {vertical}")

    conversation = _load_conversation(vertical, conversation_id)
    lead = (conversation or {}).get("lead_data") or {}

    contact = contact.strip() or lead.get("phone") or lead.get("email") or ""
    contact_type = _classify_contact(contact)

    if contact_type is None:
        raise ValueError(INVALID_CONTACT_MESSAGE)

    name = name.strip() or lead.get("name") or None
    note = note.strip() or None
    from_site = source == "widget"

    if from_site:
        message = "¡Listo! Avisé al equipo: una persona te contactará lo antes posible 🙌"
    else:
        message = "¡Listo! En una web real, esto enviaría un aviso urgente por correo al equipo 📩"

    # Un doble clic o un reintento no debe llenar el correo del dueño.
    if repository.recent_handoff_exists(vertical, contact):
        return {"status": "ok", "duplicate": True, "message": message}

    handoff_id = repository.create_handoff(
        vertical, source, conversation_id, name, contact, contact_type, note
    )

    messages = (conversation or {}).get("messages") or []

    notify_handoff_requested(
        vertical=vertical,
        source=source,
        name=name,
        contact=contact,
        note=note,
        lead=lead,
        transcript=messages[-TRANSCRIPT_LIMIT:],
    )

    return {"status": "ok", "duplicate": False, "handoff_id": handoff_id, "message": message}
