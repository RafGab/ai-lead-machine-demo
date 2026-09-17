import logging

from backend.demo import repository
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services.conversation_service import (
    process_message as process_inmobiliaria_message,
    is_closing_message,
    merge_lead_data,
)

logger = logging.getLogger(__name__)


def process_demo_message(
    vertical: str,
    message: str,
    conversation_id: int | None = None,
    field: str | None = None,
    value=None,
) -> dict:
    """
    Punto de entrada único para la demo comercial multi-rubro.

    "inmobiliaria" usa el motor real de producción tal cual
    (backend/services), para mostrar el producto insignia probado. Los
    demás rubros son de intake genérico (recoger datos + prioridad +
    confirmar cita), aislados en sus propias tablas demo_* para no
    mezclarse con datos reales de ningún cliente.
    """

    if vertical == "inmobiliaria":
        result = process_inmobiliaria_message(message, conversation_id, field, value)
        result["vertical"] = "inmobiliaria"
        return result

    module = GENERIC_VERTICALS.get(vertical)
    if module is None:
        raise ValueError(f"Rubro de demo desconocido: {vertical}")

    if conversation_id is None:
        conversation_id = repository.create_conversation(vertical)

    conversation = repository.get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"La conversación de demo {conversation_id} no existe.")

    repository.save_message(conversation_id, "user", message)

    existing_data = conversation.get("lead_data", {})

    if is_closing_message(message):
        assistant_message = (
            "¡Perfecto! Si quieres retomarlo más adelante, aquí estaré. "
            "Que tengas un buen día 👋"
        )
        repository.save_message(conversation_id, "assistant", assistant_message)

        return {
            "conversation_id": conversation_id,
            "vertical": vertical,
            "lead": existing_data,
            "result": {"status": "closed"},
            "assistant_message": assistant_message,
            "options": None,
            "options_field": None,
        }

    if field:
        new_data = {field: value}
    else:
        try:
            extracted = module.extract(message, conversation_history=conversation.get("messages", []))
            new_data = extracted.model_dump()
        except Exception:
            logger.exception("Fallo al extraer datos en demo (vertical=%s, conversation_id=%s)", vertical, conversation_id)

            assistant_message = "Lo siento, ahora mismo no puedo procesar tu mensaje. Inténtalo de nuevo en unos segundos."
            repository.save_message(conversation_id, "assistant", assistant_message)

            return {
                "conversation_id": conversation_id,
                "vertical": vertical,
                "lead": existing_data,
                "result": {"status": "error"},
                "assistant_message": assistant_message,
                "options": None,
                "options_field": None,
            }

    merged_data = merge_lead_data(existing_data, new_data)

    # cada módulo expone exactamente una clase de modelo; la localizamos
    # dinámicamente sin acoplar el orquestador a su nombre concreto.
    model_cls = _find_model_cls(module)
    lead_instance = model_cls(**merged_data)

    repository.update_lead_data(conversation_id, lead_instance.model_dump())

    next_question = module.get_next_question(lead_instance)

    if next_question:
        assistant_message = next_question
        options = None
        options_field = None
        result = {"status": "needs_information", "question": next_question}
    else:
        priority_info = module.evaluate_priority(lead_instance)
        lines = [module.BOOKING_INTRO]

        if priority_info.get("notes"):
            lines.append("")
            lines.append("📋 Notas internas para el equipo:")
            for note in priority_info["notes"]:
                lines.append(f"• {note}")

        lines.append("")
        lines.append("En breve te confirmamos por teléfono. ¡Gracias!")

        assistant_message = "\n".join(lines)
        options = None
        options_field = None
        result = {"status": "completed", "priority": priority_info.get("priority", "normal")}

    repository.save_message(conversation_id, "assistant", assistant_message)

    return {
        "conversation_id": conversation_id,
        "vertical": vertical,
        "lead": lead_instance.model_dump(),
        "result": result,
        "assistant_message": assistant_message,
        "options": options,
        "options_field": options_field,
    }


def _find_model_cls(module):
    """
    Cada módulo de vertical define exactamente una clase Pydantic
    (Patient, CaseIntake, Reservation, MembershipLead...). La ubicamos
    por convención: es la que tiene method_dump/model_fields y no es
    una función.
    """

    for name in dir(module):
        candidate = getattr(module, name)
        if isinstance(candidate, type) and hasattr(candidate, "model_fields") and name != "BaseModel":
            return candidate

    raise RuntimeError(f"No se encontró un modelo Pydantic en el módulo {module.__name__}")
