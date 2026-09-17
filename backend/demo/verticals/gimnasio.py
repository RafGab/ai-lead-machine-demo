from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option

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
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> MembershipLead:
    return call_ai(SYSTEM_PROMPT, MembershipLead, message, conversation_history)


def get_next_question(lead: MembershipLead) -> dict | None:
    if not lead.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}
    if not lead.goal:
        return {
            "text": "¿Cuál es tu objetivo principal?",
            "field": "goal",
            "options": [
                option("Perder peso", "perder peso"),
                option("Ganar masa muscular", "ganar masa muscular"),
                option("Salud general", "salud general"),
                option("Rendimiento deportivo", "rendimiento deportivo"),
            ],
        }
    if not lead.membership_type:
        return {
            "text": "¿Qué tipo de membresía te interesa?",
            "field": "membership_type",
            "options": [
                option("Mensual", "mensual"),
                option("Trimestral", "trimestral"),
                option("Anual", "anual"),
                option("Solo clases grupales", "solo clases grupales"),
            ],
        }
    if not lead.preferred_schedule:
        return {
            "text": "¿Qué horario prefieres entrenar?",
            "field": "preferred_schedule",
            "options": [option("Mañana", "mañana"), option("Tarde", "tarde"), option("Noche", "noche")],
        }
    if lead.has_medical_condition is None:
        return {
            "text": "¿Tienes alguna condición médica o lesión que debamos tener en cuenta?",
            "field": "has_medical_condition",
            "options": [option("Sí", True), option("No", False)],
        }
    if lead.wants_trial_class is None:
        return {
            "text": "¿Te gustaría agendar una clase de prueba antes de inscribirte?",
            "field": "wants_trial_class",
            "options": [option("Sí", True), option("No", False)],
        }
    if not lead.preferred_date:
        return {"text": "¿Qué día te vendría bien para tu visita?", "field": "preferred_date", "options": None}
    if not lead.phone:
        return {"text": "Por último, ¿a qué teléfono te podemos confirmar?", "field": "phone", "options": None}
    return None


def evaluate_priority(lead: MembershipLead) -> dict:
    notes = []

    if lead.has_medical_condition:
        notes.append("Condición médica mencionada: que un entrenador la revise antes de la primera sesión.")

    if lead.membership_type == "anual":
        notes.append("Interés en plan anual: ofrecer descuento o promoción vigente.")

    return {"priority": "normal", "notes": notes}
