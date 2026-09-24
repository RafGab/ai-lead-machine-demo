import logging
import time

from backend.demo import repository
from backend.demo.ai_helper import generate_followup_reply
from backend.demo.field_labels import FIELD_LABELS
from backend.demo.lead_notification import notify_lead_completed
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services.message_guards import (
    PREFIXES,
    SMALLTALK_REPLIES,
    classify_message,
    classify_smalltalk,
)
from backend.services.sanitize import FIELD_HINTS, clean_extracted, learned_something
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
    source: str = "demo",
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
        conversation_id = repository.create_conversation(vertical, source)

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

    if conversation.get("status") == "completed":
        # Ya se recogieron todos los datos: en vez de repetir siempre el
        # mismo texto, respondemos de verdad a lo que pregunte, sin
        # volver a pedirle sus datos de contacto ni inventar cifras
        # concretas (precios, disponibilidad exacta) que no conocemos.
        followup_prompt = (
            module.SYSTEM_PROMPT
            + "\n\nYa terminaste de recoger los datos de esta persona para "
            "agendar/reservar/registrar su caso — no vuelvas a pedirle "
            "nombre, teléfono ni el resto de datos ya conocidos. Ahora "
            "solo debes responder de forma útil y breve a lo que "
            "pregunte, en el mismo tono del negocio. No conoces datos "
            "operativos concretos del negocio real (precios exactos, "
            "horarios de apertura, disponibilidad en tiempo real, "
            "direcciones, políticas internas) salvo lo que ya se haya "
            "mencionado en esta conversación — para cualquiera de esos "
            "datos que no conozcas, dilo con honestidad y ofrece que el "
            "equipo se lo confirme pronto. No inventes cifras, horarios "
            "ni otros datos concretos que no tengas."
            + _registered_data_summary(existing_data)
        )

        smalltalk = classify_smalltalk(message)

        try:
            if smalltalk:
                assistant_message = SMALLTALK_REPLIES[smalltalk]
            else:
                assistant_message = generate_followup_reply(
                    followup_prompt, message, conversation_history=conversation.get("messages", [])
                )
        except Exception:
            logger.exception(
                "Fallo al generar respuesta de seguimiento post-registro (vertical=%s, conversation_id=%s)",
                vertical, conversation_id,
            )
            assistant_message = (
                "Lo siento, ahora mismo no puedo procesar tu mensaje. Inténtalo de nuevo en unos segundos."
            )

        repository.save_message(conversation_id, "assistant", assistant_message)

        return {
            "conversation_id": conversation_id,
            "vertical": vertical,
            "lead": existing_data,
            "result": {"status": "completed", "booking_available": True},
            "assistant_message": assistant_message,
            "options": None,
            "options_field": None,
        }

    nothing_understood = False
    guard = None

    if field:
        new_data = {field: value}
    elif guard := classify_message(
        message, module.get_next_question(_find_model_cls(module)(**existing_data))
    ):
        # Mensaje sin datos que extraer (una pregunta, "ok", un intento de
        # inyección...): no se llama a la IA, que podría rellenar algo.
        new_data = {}
    else:
        last_error = None
        new_data = None
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                extracted = module.extract(message, conversation_history=conversation.get("messages", []))
                new_data = extracted.model_dump()
                break
            except Exception as error:
                last_error = error
                if attempt < max_attempts - 1:
                    time.sleep(1)

        if new_data is None:
            logger.exception(
                "Fallo al extraer datos en demo tras reintentar (vertical=%s, conversation_id=%s)",
                vertical, conversation_id, exc_info=last_error,
            )

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

    new_data, rejected_fields = clean_extracted(new_data, message)

    if not field:
        # Solo cuenta como "no entendido" si ya había una pregunta previa
        # que responder (el primer "hola" no aporta datos y es normal) y el
        # mensaje no aporta nada NUEVO: el modelo suele devolver otra vez
        # los datos que ya conocía, así que hay que compararlos.
        nothing_understood = (
            bool(conversation.get("messages"))
            and not learned_something(existing_data, new_data)
        )

    merged_data = merge_lead_data(existing_data, new_data)

    # cada módulo expone exactamente una clase de modelo; la localizamos
    # dinámicamente sin acoplar el orquestador a su nombre concreto.
    model_cls = _find_model_cls(module)
    lead_instance = model_cls(**merged_data)

    repository.update_lead_data(conversation_id, lead_instance.model_dump())

    next_question = module.get_next_question(lead_instance)

    if next_question:
        assistant_message = next_question["text"]
        hint = next((FIELD_HINTS[f] for f in rejected_fields if f in FIELD_HINTS), None)
        if hint:
            asked_again = next_question["field"] in rejected_fields
            assistant_message = hint if asked_again else hint + " " + assistant_message
        elif guard:
            assistant_message = PREFIXES[guard] + " " + assistant_message
        elif nothing_understood:
            assistant_message = PREFIXES["unclear"] + " " + assistant_message
        options = next_question.get("options")
        options_field = next_question.get("field")
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
        result = {
            "status": "completed",
            "priority": priority_info.get("priority", "normal"),
            "booking_available": True,
        }
        repository.mark_completed(conversation_id)

        try:
            notify_lead_completed(
                vertical=vertical,
                source=conversation.get("source", source),
                lead=lead_instance.model_dump(),
                priority=priority_info.get("priority", "normal"),
                notes=priority_info.get("notes"),
            )
        except Exception:
            logger.exception("Fallo al avisar del lead completado (vertical=%s)", vertical)

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


def _registered_data_summary(lead_data: dict) -> str:
    lines = [
        f"- {FIELD_LABELS.get(field, field)}: {value}"
        for field, value in lead_data.items()
        if value not in (None, "", False)
    ]

    if not lines:
        return ""

    header = "Datos ya registrados de esta persona (no se los vuelvas a pedir):"

    return "\n\n" + header + "\n" + "\n".join(lines)


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
