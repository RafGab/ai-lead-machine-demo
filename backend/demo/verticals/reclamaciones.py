from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option

LABEL = "Reclamaciones bancarias"
ICON = "⚖️"
COLOR = "#BC1580"
WELCOME = (
    "Hola, soy el asistente del despacho. Cuéntame brevemente tu caso y te ayudo "
    "a reservar tu primera consulta gratuita."
)
BOOKING_INTRO = "Gracias, ya tengo lo necesario para reservar tu primera consulta con un abogado."

BANK_CASES = {"revolving", "hipoteca", "prestamo_personal", "prestamo_coche"}
CASE_TYPES = [
    "revolving", "hipoteca", "prestamo_personal", "prestamo_coche",
    "laboral", "administrativo", "civil", "mercantil", "otro",
]


class ReclamacionLead(BaseModel):
    name: str | None = None
    phone: str | None = None
    case_type: str | None = None
    entity: str | None = None
    has_documents: str | None = None
    case_summary: str | None = None
    has_deadline: bool | None = None
    deadline_date: str | None = None
    preferred_date: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de un despacho de abogados online especializado en "
    "reclamaciones bancarias (tarjetas revolving, hipotecas, préstamos "
    "personales y micropréstamos, préstamos de coche) y también en derecho "
    "laboral, administrativo, civil y mercantil.\n\n"
    "Tu única función es recoger los datos necesarios para reservar una "
    "primera consulta con un abogado: nombre, teléfono, tipo de caso, "
    "entidad financiera (si es un caso bancario), si el cliente tiene a mano "
    "los contratos o extractos, un resumen breve del caso, si hay alguna "
    "notificación o plazo en curso y qué día le vendría bien.\n\n"
    "IMPORTANTE: nunca des asesoría legal, ni opines sobre si el caso es "
    "viable, ni prometas ni estimes cantidades a recuperar, ni interpretes "
    "leyes, sentencias o plazos concretos. Eso lo hace el abogado en la "
    "consulta. Tampoco menciones honorarios: si preguntan, di que el abogado "
    "se lo explica en la primera consulta.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está presente, "
    "devuelve None. No inventes nada.\n\n"
    "Para case_type utiliza únicamente: revolving, hipoteca, prestamo_personal, "
    "prestamo_coche, laboral, administrativo, civil, mercantil, otro.\n"
    "Para has_documents utiliza únicamente: si, parcial, no.\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un nombre "
    "de persona. Si el texto no tiene sentido como nombre, deja name como None.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' teniendo "
    "en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> ReclamacionLead:
    return call_ai(SYSTEM_PROMPT, ReclamacionLead, message, conversation_history)


def get_next_question(case: ReclamacionLead) -> dict | None:
    if not case.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}

    if not case.case_type:
        return {
            "text": "¿Con qué tipo de caso necesitas ayuda?",
            "field": "case_type",
            "options": [
                option("Tarjeta revolving", "revolving"),
                option("Hipoteca", "hipoteca"),
                option("Préstamo personal o micropréstamo", "prestamo_personal"),
                option("Préstamo de coche", "prestamo_coche"),
                option("Laboral", "laboral"),
                option("Administrativo", "administrativo"),
                option("Civil", "civil"),
                option("Mercantil", "mercantil"),
                option("Otro", "otro"),
            ],
        }

    if case.case_type in BANK_CASES:
        if not case.entity:
            return {"text": "¿Qué entidad financiera es?", "field": "entity", "options": None}

        if not case.has_documents:
            return {
                "text": "¿Tienes a mano el contrato o los extractos?",
                "field": "has_documents",
                "options": [
                    option("Sí, los tengo", "si"),
                    option("Solo algunos", "parcial"),
                    option("No los tengo", "no"),
                ],
            }

    if not case.case_summary:
        return {"text": "Cuéntame brevemente de qué se trata tu caso.", "field": "case_summary", "options": None}

    if case.has_deadline is None:
        return {
            "text": "¿Has recibido alguna notificación, carta o demanda con una fecha límite?",
            "field": "has_deadline",
            "options": [option("Sí", True), option("No", False)],
        }

    if case.has_deadline and not case.deadline_date:
        return {"text": "¿Cuál es esa fecha límite?", "field": "deadline_date", "options": None}

    if not case.preferred_date:
        return {
            "text": "¿Qué día te vendría bien para la primera consulta (llamada o videollamada)?",
            "field": "preferred_date",
            "options": None,
        }

    if not case.phone:
        return {
            "text": "Por último, ¿a qué teléfono te podemos confirmar la cita?",
            "field": "phone",
            "options": None,
        }

    return None


def evaluate_priority(case: ReclamacionLead) -> dict:
    notes = []

    if case.has_deadline:
        notes.append(
            "Hay una fecha límite indicada por el cliente"
            + (f" ({case.deadline_date})" if case.deadline_date else "")
            + ": ofrecer la cita más próxima y avisar al abogado antes de la consulta."
        )

    if case.case_type in BANK_CASES and case.has_documents in ("no", "parcial"):
        notes.append(
            "Documentación incompleta: pedir al cliente contrato y extractos antes de la consulta."
        )

    return {"priority": "alta" if case.has_deadline else "normal", "notes": notes}
