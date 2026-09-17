from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option
from backend.services.matching import get_available_cities

LABEL = "Propietarios"
ICON = "🔑"
COLOR = "#a3792f"
WELCOME = (
    "¡Hola! ¿Tienes un piso y quieres alquilarlo por habitaciones sin gestionar nada tú? "
    "Nosotros lo reformamos, lo alquilamos y te pagamos una renta mensual garantizada. "
    "Cuéntame sobre tu piso."
)
BOOKING_INTRO = "¡Perfecto! Ya tengo los datos de tu piso para que un gestor lo valore."


class OwnerLead(BaseModel):
    name: str | None = None
    phone: str | None = None
    city: str | None = None
    address: str | None = None
    size_m2: int | None = None
    bedrooms: int | None = None
    current_status: str | None = None
    needs_renovation: bool | None = None
    preferred_date: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de captación de propietarios para una gestora "
    "inmobiliaria. El modelo de negocio: el propietario cede su piso, la "
    "gestora lo reforma si hace falta y lo alquila por habitaciones; el "
    "propietario no gestiona nada — solo recibe una renta mensual "
    "garantizada, esté o no esté alquilada cada habitación.\n\n"
    "Tu única función es recoger los datos del piso para que un gestor "
    "haga una valoración: nombre, teléfono, ciudad, dirección "
    "aproximada (calle o zona, no hace falta el número exacto), metros "
    "cuadrados, número de habitaciones, si el piso está actualmente "
    "alquilado, vacío o en uso propio, si crees que necesita reforma, y "
    "qué día le vendría bien para una llamada de valoración.\n\n"
    "IMPORTANTE: nunca prometas una cifra concreta de renta ni "
    "condiciones del contrato de cesión — eso lo define el gestor "
    "humano tras valorar el piso. Puedes reforzar el mensaje general "
    "(renta garantizada, cero gestión) pero no inventes números.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para current_status utiliza únicamente:\n"
    "- alquilado\n- vacío\n- uso propio\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> OwnerLead:
    return call_ai(SYSTEM_PROMPT, OwnerLead, message, conversation_history)


def get_next_question(owner: OwnerLead) -> dict | None:
    if not owner.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}
    if not owner.city:
        cities = get_available_cities()
        return {
            "text": "¿En qué ciudad está el piso?",
            "field": "city",
            "options": [option(c, c) for c in cities] if cities else None,
        }
    if not owner.address:
        return {
            "text": "¿En qué calle o zona se encuentra? (no hace falta el número exacto)",
            "field": "address",
            "options": None,
        }
    if owner.size_m2 is None:
        return {"text": "¿Cuántos metros cuadrados tiene aproximadamente?", "field": "size_m2", "options": None}
    if owner.bedrooms is None:
        return {
            "text": "¿Cuántas habitaciones tiene?",
            "field": "bedrooms",
            "options": [option("1", 1), option("2", 2), option("3", 3), option("4 o más", 4)],
        }
    if not owner.current_status:
        return {
            "text": "¿El piso está actualmente alquilado, vacío o lo usas tú?",
            "field": "current_status",
            "options": [option("Alquilado", "alquilado"), option("Vacío", "vacío"), option("Uso propio", "uso propio")],
        }
    if owner.needs_renovation is None:
        return {
            "text": "¿Consideras que necesita alguna reforma antes de alquilarlo?",
            "field": "needs_renovation",
            "options": [option("Sí", True), option("No", False)],
        }
    if not owner.preferred_date:
        return {
            "text": "¿Qué día te vendría bien para que te llame un gestor y valore el piso?",
            "field": "preferred_date",
            "options": None,
        }
    if not owner.phone:
        return {"text": "Por último, ¿a qué teléfono te podemos llamar?", "field": "phone", "options": None}
    return None


def evaluate_priority(owner: OwnerLead) -> dict:
    notes = []

    if owner.needs_renovation:
        notes.append("Necesita reforma: preparar presupuesto estimado antes de la llamada.")

    if owner.current_status == "alquilado":
        notes.append("Piso actualmente alquilado: confirmar fecha de fin del contrato vigente.")

    if owner.bedrooms and owner.bedrooms >= 4:
        notes.append("Piso grande (4+ habitaciones): buen potencial de rentabilidad por habitaciones.")

    return {"priority": "normal", "notes": notes}
