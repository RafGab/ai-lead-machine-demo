from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option

LABEL = "Acero Pulido"
ICON = "✈️"
COLOR = "#7f1626"
WELCOME = (
    "¡Hola! Soy el asistente de Acero Pulido, asesoría de extranjería. "
    "Te ayudo a dar el primer paso con tu trámite. Cuéntame, ¿en qué te puedo ayudar?"
)
BOOKING_INTRO = "¡Perfecto! Ya tengo tus datos para que un asesor de Acero Pulido revise tu caso."

PROCEDURES = [
    "estancia por estudios",
    "visa de estudios",
    "reagrupación familiar",
    "modificación de estancia a residencia",
    "canje de licencia",
]

EDUCATION_LEVELS = [
    "educación secundaria",
    "formación profesional / técnico",
    "universitario",
    "postgrado / máster / doctorado",
]


class ExtranjeriaLead(BaseModel):
    name: str | None = None
    current_country: str | None = None
    nationality: str | None = None
    education_level: str | None = None
    procedure: str | None = None
    phone: str | None = None
    email: str | None = None
    contact_hours: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de Acero Pulido, una asesoría de extranjería "
    "especializada en trámites para estudiantes y residentes extranjeros "
    "en España.\n\n"
    "Tu única función es recoger los datos necesarios para que un asesor "
    "evalúe el caso: nombre, país de residencia actual, nacionalidad, "
    "nivel de estudios culminados, qué trámite necesita realizar, "
    "teléfono, correo electrónico, y en qué horas se le puede contactar.\n\n"
    "IMPORTANTE: nunca des asesoría legal ni migratoria, ni opines sobre "
    "la viabilidad de un trámite, plazos legales o requisitos concretos "
    "— eso lo hace el asesor humano tras revisar el caso. Tu trabajo es "
    "solo recopilar la información, no evaluarla.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para procedure utiliza únicamente:\n"
    "- estancia por estudios\n- visa de estudios\n- reagrupación familiar\n"
    "- modificación de estancia a residencia\n- canje de licencia\n\n"
    "Para education_level utiliza únicamente:\n"
    "- educación secundaria\n- formación profesional / técnico\n"
    "- universitario\n- postgrado / máster / doctorado\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> ExtranjeriaLead:
    return call_ai(SYSTEM_PROMPT, ExtranjeriaLead, message, conversation_history)


def get_next_question(lead: ExtranjeriaLead) -> dict | None:
    if not lead.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}
    if not lead.current_country:
        return {
            "text": "¿En qué país resides actualmente?",
            "field": "current_country",
            "options": None,
        }
    if not lead.nationality:
        return {"text": "¿Cuál es tu nacionalidad?", "field": "nationality", "options": None}
    if not lead.education_level:
        return {
            "text": "¿Cuál es tu nivel de estudios culminados?",
            "field": "education_level",
            "options": [
                option("Educación secundaria", "educación secundaria"),
                option("Formación profesional / Técnico", "formación profesional / técnico"),
                option("Universitario", "universitario"),
                option("Postgrado / Máster / Doctorado", "postgrado / máster / doctorado"),
            ],
        }
    if not lead.procedure:
        return {
            "text": "¿Qué trámite necesitas realizar?",
            "field": "procedure",
            "options": [
                option("Estancia por estudios", "estancia por estudios"),
                option("Visa de estudios", "visa de estudios"),
                option("Reagrupación familiar", "reagrupación familiar"),
                option("Modificación de estancia a residencia", "modificación de estancia a residencia"),
                option("Canje de licencia", "canje de licencia"),
            ],
        }
    if not lead.phone:
        return {"text": "¿A qué número de teléfono te podemos contactar?", "field": "phone", "options": None}
    if not lead.email:
        return {"text": "¿Cuál es tu correo electrónico?", "field": "email", "options": None}
    if not lead.contact_hours:
        return {
            "text": "¿En qué horario prefieres que te contactemos?",
            "field": "contact_hours",
            "options": [
                option("Mañana", "mañana"),
                option("Tarde", "tarde"),
                option("Noche", "noche"),
                option("Cualquier hora", "cualquier hora"),
            ],
        }
    return None


def evaluate_priority(lead: ExtranjeriaLead) -> dict:
    notes = []

    if lead.procedure == "reagrupación familiar":
        notes.append("Reagrupación familiar: preparar checklist de documentación del familiar reagrupado.")

    if lead.procedure == "modificación de estancia a residencia":
        notes.append("Cambio de estancia a residencia: confirmar tiempo que lleva en España y estado del expediente.")

    if lead.procedure in ("estancia por estudios", "visa de estudios"):
        notes.append("Trámite de estudios: confirmar si ya tiene carta de admisión de un centro educativo.")

    return {"priority": "normal", "notes": notes}
