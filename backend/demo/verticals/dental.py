from pydantic import BaseModel

from backend.demo.ai_helper import call_ai

LABEL = "Clínica Dental"
ICON = "🦷"
COLOR = "#2f7d6e"
WELCOME = "¡Hola! Soy el asistente de recepción de la clínica. ¿En qué puedo ayudarte hoy?"
BOOKING_INTRO = "¡Perfecto! Con esto ya tengo lo necesario para agendar tu cita."


class Patient(BaseModel):
    name: str | None = None
    phone: str | None = None
    reason: str | None = None
    specialty: str | None = None
    is_urgent: bool | None = None
    has_insurance: bool | None = None
    insurance_provider: str | None = None
    preferred_date: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de recepción de una clínica dental.\n\n"
    "Tu única función es recoger los datos necesarios para agendar una "
    "cita: nombre, teléfono, motivo de consulta, si es urgente, la "
    "especialidad, si tiene seguro dental y con qué compañía, y qué día "
    "le vendría bien.\n\n"
    "IMPORTANTE: nunca des consejo médico, ni diagnostiques, ni valores "
    "la gravedad de ningún síntoma. Si el paciente describe dolor o una "
    "urgencia, marca is_urgent=True y limítate a decir que se le dará "
    "prioridad en la agenda; no opines sobre la causa ni el tratamiento.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para specialty utiliza valores como:\n"
    "- odontología general\n- ortodoncia\n- implantes\n"
    "- estética dental\n- endodoncia\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> Patient:
    return call_ai(SYSTEM_PROMPT, Patient, message, conversation_history)


def get_next_question(patient: Patient) -> str | None:
    if not patient.name:
        return "Para empezar, ¿cuál es tu nombre?"
    if not patient.reason:
        return "¿Cuál es el motivo de tu consulta?"
    if patient.is_urgent is None:
        return "¿Es urgente? ¿Tienes dolor ahora mismo?"
    if not patient.specialty:
        return "¿Qué tipo de consulta necesitas (general, ortodoncia, implantes, estética)?"
    if patient.has_insurance is None:
        return "¿Tienes seguro dental?"
    if patient.has_insurance and not patient.insurance_provider:
        return "¿Con qué compañía de seguro dental?"
    if not patient.preferred_date:
        return "¿Qué día te vendría bien para la cita?"
    if not patient.phone:
        return "Por último, ¿a qué teléfono te podemos confirmar la cita?"
    return None


def evaluate_priority(patient: Patient) -> dict:
    notes = []

    if patient.is_urgent:
        notes.append(
            "Urgencia: ofrecer el primer hueco disponible, aunque sea "
            "fuera del horario habitual de agenda."
        )

    if patient.specialty == "implantes" and not patient.has_insurance:
        notes.append(
            "Sin seguro + implantes: informar de que es un tratamiento "
            "con presupuesto previo antes de la cita."
        )

    return {"priority": "alta" if patient.is_urgent else "normal", "notes": notes}
