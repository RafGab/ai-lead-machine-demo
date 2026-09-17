from pydantic import BaseModel

from backend.demo.ai_helper import call_ai

LABEL = "Gimnasio"
ICON = "💪"
COLOR = "#ab263e"
WELCOME = "¡Hola! Soy el asistente del gimnasio. ¿Buscas información sobre planes o quieres agendar una clase de prueba?"
BOOKING_INTRO = "¡Listo! Ya tengo lo necesario para agendar tu visita."


class MembershipLead(BaseModel):
    name: str | None = None
    phone: str | None = None
    goal: str | None = None
    membership_type: str | None = None
    preferred_schedule: str | None = None
    has_medical_condition: bool | None = None
    wants_trial_class: bool | None = None
    preferred_date: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente comercial de un gimnasio.\n\n"
    "Tu única función es recoger los datos necesarios para agendar una "
    "clase de prueba o una visita para inscripción: nombre, teléfono, "
    "objetivo (pérdida de peso, ganancia muscular, salud general, "
    "rendimiento deportivo), tipo de membresía de interés, horario "
    "preferido, si tiene alguna condición médica a considerar, si "
    "quiere clase de prueba, y qué día le vendría bien.\n\n"
    "IMPORTANTE: nunca des consejo médico ni de entrenamiento, ni "
    "evalúes riesgos de salud. Si menciona una condición médica o "
    "lesión, marca has_medical_condition=True y limítate a decir que "
    "un entrenador lo revisará antes de la primera sesión; no opines "
    "sobre si puede o no entrenar.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para membership_type utiliza valores como:\n"
    "- mensual\n- trimestral\n- anual\n- solo clases grupales\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> MembershipLead:
    return call_ai(SYSTEM_PROMPT, MembershipLead, message, conversation_history)


def get_next_question(lead: MembershipLead) -> str | None:
    if not lead.name:
        return "Para empezar, ¿cuál es tu nombre?"
    if not lead.goal:
        return "¿Cuál es tu objetivo principal (perder peso, ganar masa muscular, salud general, rendimiento deportivo)?"
    if not lead.membership_type:
        return "¿Qué tipo de membresía te interesa: mensual, trimestral, anual o solo clases grupales?"
    if not lead.preferred_schedule:
        return "¿Qué horario prefieres entrenar (mañana, tarde, noche)?"
    if lead.has_medical_condition is None:
        return "¿Tienes alguna condición médica o lesión que debamos tener en cuenta?"
    if lead.wants_trial_class is None:
        return "¿Te gustaría agendar una clase de prueba antes de inscribirte?"
    if not lead.preferred_date:
        return "¿Qué día te vendría bien para tu visita?"
    if not lead.phone:
        return "Por último, ¿a qué teléfono te podemos confirmar?"
    return None


def evaluate_priority(lead: MembershipLead) -> dict:
    notes = []

    if lead.has_medical_condition:
        notes.append("Condición médica mencionada: que un entrenador la revise antes de la primera sesión.")

    if lead.membership_type == "anual":
        notes.append("Interés en plan anual: ofrecer descuento o promoción vigente.")

    return {"priority": "normal", "notes": notes}
