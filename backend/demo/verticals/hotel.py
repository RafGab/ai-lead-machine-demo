from pydantic import BaseModel

from backend.demo.ai_helper import call_ai, option

LABEL = "Hotel"
ICON = "🏨"
COLOR = "#a3792f"
WELCOME = "¡Bienvenido/a! Soy el asistente de reservas del hotel. ¿Para cuándo te gustaría reservar?"
BOOKING_INTRO = "¡Genial! Ya tengo todo lo necesario para confirmar tu reserva."


class Reservation(BaseModel):
    name: str | None = None
    phone: str | None = None
    check_in_date: str | None = None
    check_out_date: str | None = None
    guests: int | None = None
    room_type: str | None = None
    has_pets: bool | None = None
    special_request: str | None = None


SYSTEM_PROMPT = (
    "Eres el asistente de reservas de un hotel.\n\n"
    "Tu única función es recoger los datos necesarios para confirmar "
    "una reserva: nombre, teléfono, fecha de entrada, fecha de salida, "
    "número de huéspedes, tipo de habitación, si viaja con mascota, y "
    "cualquier petición especial (cuna, vista, piso alto, etc.).\n\n"
    "IMPORTANTE: nunca confirmes disponibilidad real ni precios "
    "concretos — eso lo valida el hotel después. Solo recopila la "
    "información de la solicitud.\n\n"
    "Analiza la conversación y extrae únicamente información que esté "
    "presente o que pueda deducirse claramente. Si un dato no está "
    "presente, devuelve None. No inventes nada.\n\n"
    "Para room_type utiliza únicamente:\n"
    "- individual\n- doble\n- suite\n- familiar\n\n"
    "Para guests utiliza el número total de personas que se hospedarán.\n\n"
    "Si el cliente indica que NO viaja con mascota, has_pets debe ser "
    "False. Si indica que sí, debe ser True.\n\n"
    "Para 'name': solo devuélvelo si el mensaje razonablemente parece un "
    "nombre de persona. Si el texto no tiene sentido como nombre (frases "
    "random, números sueltos, texto sin sentido), deja name como None — "
    "no lo inventes ni aceptes cualquier cosa como si fuera un nombre.\n\n"
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> Reservation:
    return call_ai(SYSTEM_PROMPT, Reservation, message, conversation_history)


def get_next_question(reservation: Reservation) -> dict | None:
    if not reservation.name:
        return {"text": "Para empezar, ¿cuál es tu nombre?", "field": "name", "options": None}
    if not reservation.check_in_date:
        return {"text": "¿Para qué fecha de entrada?", "field": "check_in_date", "options": None}
    if not reservation.check_out_date:
        return {"text": "¿Y la fecha de salida?", "field": "check_out_date", "options": None}
    if reservation.guests is None:
        return {
            "text": "¿Cuántas personas se van a hospedar?",
            "field": "guests",
            "options": [option("1", 1), option("2", 2), option("3", 3), option("4 o más", 4)],
        }
    if not reservation.room_type:
        return {
            "text": "¿Qué tipo de habitación prefieres?",
            "field": "room_type",
            "options": [
                option("Individual", "individual"),
                option("Doble", "doble"),
                option("Suite", "suite"),
                option("Familiar", "familiar"),
            ],
        }
    if reservation.has_pets is None:
        return {
            "text": "¿Viajas con alguna mascota?",
            "field": "has_pets",
            "options": [option("Sí", True), option("No", False)],
        }
    if not reservation.special_request:
        return {
            "text": "¿Alguna petición especial (cuna, vista, piso alto)? Puedes escribirla o marcar que no tienes.",
            "field": "special_request",
            "options": [option("Ninguna", "ninguna")],
        }
    if not reservation.phone:
        return {
            "text": "Por último, ¿a qué teléfono te podemos confirmar la reserva?",
            "field": "phone",
            "options": None,
        }
    return None


def evaluate_priority(reservation: Reservation) -> dict:
    notes = []

    if reservation.has_pets:
        notes.append("Viaja con mascota: asignar una habitación pet-friendly.")

    if reservation.guests and reservation.guests >= 4:
        notes.append("Grupo grande: verificar habitaciones familiares o conectadas.")

    return {"priority": "normal", "notes": notes}
