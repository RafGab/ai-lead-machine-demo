from pydantic import BaseModel

from backend.demo.ai_helper import call_ai

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
    "MUY IMPORTANTE: interpreta las respuestas cortas como 'sí' o 'no' "
    "teniendo en cuenta la pregunta inmediatamente anterior."
)


def extract(message: str, conversation_history: list[dict] | None = None) -> Reservation:
    return call_ai(SYSTEM_PROMPT, Reservation, message, conversation_history)


def get_next_question(reservation: Reservation) -> str | None:
    if not reservation.name:
        return "Para empezar, ¿cuál es tu nombre?"
    if not reservation.check_in_date:
        return "¿Para qué fecha de entrada?"
    if not reservation.check_out_date:
        return "¿Y la fecha de salida?"
    if reservation.guests is None:
        return "¿Cuántas personas se van a hospedar?"
    if not reservation.room_type:
        return "¿Qué tipo de habitación prefieres: individual, doble, suite o familiar?"
    if reservation.has_pets is None:
        return "¿Viajas con alguna mascota?"
    if not reservation.special_request:
        return "¿Alguna petición especial (cuna, vista, piso alto)? Si no, escribe 'ninguna'."
    if not reservation.phone:
        return "Por último, ¿a qué teléfono te podemos confirmar la reserva?"
    return None


def evaluate_priority(reservation: Reservation) -> dict:
    notes = []

    if reservation.has_pets:
        notes.append("Viaja con mascota: asignar una habitación pet-friendly.")

    if reservation.guests and reservation.guests >= 4:
        notes.append("Grupo grande: verificar habitaciones familiares o conectadas.")

    return {"priority": "normal", "notes": notes}
