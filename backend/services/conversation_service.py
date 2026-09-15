import logging

from backend.models.lead import Lead
from backend.services.ai_service import extract_lead_data
from backend.services.questions import get_next_question
from backend.services.rules import validate_room_rules
from backend.services.matching import find_matching_properties
from backend.services.conversation_repository import (
    create_conversation,
    save_message,
    get_conversation,
    update_lead_data,
)

logger = logging.getLogger(__name__)


def process_lead(lead: Lead) -> dict:

    # 1. Comprobar reglas específicas de habitaciones
    if lead.property_type == "habitacion":
        validation = validate_room_rules(lead)

        if not validation["compatible"]:
            return {
                "status": "incompatible",
                "message": "El cliente no cumple los requisitos.",
                "details": validation
            }

    # 2. Comprobar si falta información
    next_question = get_next_question(lead)

    if next_question:
        return {
            "status": "needs_information",
            "question": next_question
        }

    # 3. Buscar propiedades compatibles
    properties = find_matching_properties(lead)

    # 4. Si no encontramos propiedades
    if not properties:
        return {
            "status": "no_results",
            "message": "No encontramos propiedades que coincidan con los criterios."
        }

    # 5. Devolver propiedades encontradas
    return {
        "status": "matches_found",
        "message": "Hemos encontrado propiedades que pueden encajar.",
        "properties": properties
    }


def merge_lead_data(
    existing_lead: dict,
    new_data: dict
) -> dict:
    """
    Combina los datos anteriores del Lead con
    la información obtenida del nuevo mensaje.

    Los valores nuevos solamente sustituyen a los
    anteriores cuando realmente fueron detectados.
    """

    merged = existing_lead.copy()

    for field, value in new_data.items():

        if value is not None:
            merged[field] = value

    return merged


def process_message(
    message: str,
    conversation_id: int | None = None
) -> dict:
    """
    Procesa un mensaje dentro de una conversación.

    Si no se proporciona conversation_id, crea una
    nueva conversación automáticamente.
    """

    # ---------------------------------------------------------
    # 1. Crear o recuperar conversación
    # ---------------------------------------------------------

    if conversation_id is None:
        conversation_id = create_conversation()

    conversation = get_conversation(conversation_id)

    if conversation is None:
        raise ValueError(
            f"La conversación {conversation_id} no existe."
        )

    # ---------------------------------------------------------
    # 2. Guardar el mensaje del usuario
    # ---------------------------------------------------------

    save_message(
        conversation_id,
        "user",
        message
    )

    # ---------------------------------------------------------
    # 3. Recuperar Lead anterior
    # ---------------------------------------------------------

    existing_lead = conversation.get(
        "lead_data",
        {}
    )

    # ---------------------------------------------------------
    # 4. Extraer información del mensaje
    # ---------------------------------------------------------

    try:
        ai_data = extract_lead_data(message)
        new_data = ai_data.model_dump()
    except Exception:
        logger.exception(
            "Fallo al extraer datos del lead con la IA "
            "(conversation_id=%s)",
            conversation_id
        )

        assistant_message = (
            "Lo siento, ahora mismo no puedo procesar tu mensaje. "
            "Inténtalo de nuevo en unos segundos."
        )

        save_message(
            conversation_id,
            "assistant",
            assistant_message
        )

        return {
            "conversation_id": conversation_id,
            "lead": existing_lead,
            "result": {"status": "error"},
            "assistant_message": assistant_message
        }

    # ---------------------------------------------------------
    # 5. Combinar información anterior + nueva
    # ---------------------------------------------------------

    merged_data = merge_lead_data(
        existing_lead,
        new_data
    )

    # ---------------------------------------------------------
    # 6. Crear Lead actualizado
    # ---------------------------------------------------------

    lead = Lead(
        **merged_data
    )

    # ---------------------------------------------------------
    # 7. Guardar Lead actualizado
    # ---------------------------------------------------------

    update_lead_data(
        conversation_id,
        lead.model_dump()
    )

    # 8. Procesar Lead
    # ---------------------------------------------------------

    result = process_lead(lead)

    # ---------------------------------------------------------
    # 9. Construir respuesta del agente
    # ---------------------------------------------------------

    assistant_message = None

    if result.get("question"):

        assistant_message = result["question"]

    elif result.get("status") == "matches_found":

        properties = result.get("properties", [])

        lines = [
            "He encontrado estas opciones que pueden encajar:"
        ]

        for property in properties:

            title = property.get("title", "Propiedad")
            price = property.get("price")

            lines.append(
                f"🏠 {title}"
            )

            if price is not None:
                lines.append(
                    f"💶 {price:.0f} €/mes"
                )

        assistant_message = "\n".join(lines)

    elif result.get("status") == "no_results":

        assistant_message = (
            "Ahora mismo no encontramos propiedades "
            "que coincidan con tus criterios."
        )

    elif result.get("status") == "incompatible":

        assistant_message = result.get(
            "message",
            "Lo siento, no cumples los requisitos de esta propiedad."
        )

    # ---------------------------------------------------------
    # 10. Guardar respuesta del agente
    # ---------------------------------------------------------

    if assistant_message:

        save_message(
            conversation_id,
            "assistant",
            assistant_message
        )

    # ---------------------------------------------------------
    # 11. Devolver información
    # ---------------------------------------------------------

    return {
        "conversation_id": conversation_id,
        "lead": lead.model_dump(),
        "result": result,
        "assistant_message": assistant_message
    }