from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option

LABEL = "Despacho de Abogados"
ICON = "⚖️"
COLOR = "#1f3a5f"
WELCOME = "Hola, soy el asistente del despacho. Cuéntame brevemente tu caso y te ayudo a agendar una primera consulta."
BOOKING_INTRO = "Gracias, ya tengo lo necesario para agendar tu primera consulta."


class CaseIntake(BaseModel):
    name: str | None = None
    phone: str | None = None
    area: str | None = None
    case_summary: str | None = None
    has_deadline: bool | None = None
    deadline_date: str | None = None
    opposing_party_exists: bool | None = None
    preferred_date: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de intake de un despacho de abogados generalista "
    "(áreas: laboral, civil, familia, mercantil, penal y extranjería).\n\n"
    "Tu única función es recoger los datos necesarios para agendar una "
    "primera consulta con un abogado: nombre, teléfono, área del "
    "derecho, un resumen breve del caso, si hay un plazo legal "
    "corriendo, si hay una contraparte identificada, y qué día le "
    "vendría bien.\n\n"
    "IMPORTANTE: nunca des asesoría legal, ni opines sobre la viabilidad "
    "del caso, ni interpretes leyes o plazos legales concretos — eso lo "
    "hace el abogado en la consulta. Tu trabajo es solo recopilar la "
    "información, no evaluarla.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para area utiliza únicamente:\n"
    "- laboral\n- civil\n- familia\n- mercantil\n- penal\n- extranjería\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> CaseIntake:
    return call_ai(SYSTEM_PROMPT, CaseIntake, message, conversation_history)


def get_next_question(case: CaseIntake) -> dict | None:
    if not case.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}
    if not case.area:
        return {
            "text": "¿En qué área necesitas asesoría?",
            "field": "area",
            "options": [
                option("Laboral", "laboral"),
                option("Civil", "civil"),
                option("Familia", "familia"),
                option("Mercantil", "mercantil"),
                option("Penal", "penal"),
                option("Extranjería", "extranjería"),
            ],
        }
    if not case.case_summary:
        return {"text": "Cuéntame brevemente de qué se trata tu caso.", "field": "case_summary", "options": None}
    if case.has_deadline is None:
        return {
            "text": "¿Tienes algún plazo legal corriendo (una notificación, una demanda, una citación)?",
            "field": "has_deadline",
            "options": [option("Sí", True), option("No", False)],
        }
    if case.has_deadline and not case.deadline_date:
        return {"text": "¿Para cuándo es ese plazo?", "field": "deadline_date", "options": None}
    if case.opposing_party_exists is None:
        return {
            "text": "¿Ya hay una contraparte identificada (persona, empresa o entidad)?",
            "field": "opposing_party_exists",
            "options": [option("Sí", True), option("No", False)],
        }
    if not case.preferred_date:
        return {"text": "¿Qué día te vendría bien para la primera consulta?", "field": "preferred_date", "options": None}
    if not case.phone:
        return {
            "text": "Por último, ¿a qué teléfono te podemos confirmar la cita?",
            "field": "phone",
            "options": None,
        }
    return None


def evaluate_priority(case: CaseIntake) -> dict:
    notes = []

    if case.has_deadline:
        notes.append(
            "Plazo legal en curso: ofrecer la cita más próxima posible "
            "y avisar al abogado antes de la consulta."
        )

    if case.area == "penal":
        notes.append("Área penal: confirmar disponibilidad del abogado penalista específicamente.")

    return {"priority": "alta" if case.has_deadline else "normal", "notes": notes}
