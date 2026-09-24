import re
import unicodedata

# Filtros que se aplican ANTES de llamar a la IA. Con el prompt solo no
# basta: probando con la IA real, "ok", "no sé" o "¿cuánto cuesta?" acababan
# marcando campos sí/no (p. ej. "urgente" en una clínica) y "ignora tus
# instrucciones" se trataba como una respuesta. Aquí se decide sin IA qué
# mensajes no contienen ningún dato que extraer.

INJECTION_PATTERN = re.compile(
    r"\b(ignora|ignore|olvida|olvidate de)\b.*\b(instruccion(es)?|reglas|prompt)\b"
    r"|\bprompt\b|\bsystem\b|\bjailbreak\b|\bactua como\b|\bfinge (ser|que)\b"
)

QUESTION_START = re.compile(
    r"^(cuanto|cuanta|cuantos|cuantas|que|como|donde|cuando|quien|quienes|cual|cuales|"
    r"por que|para que|eres|sois|tienes|tienen|teneis|puedo|puedes|pueden|hay|hacen|"
    r"aceptan|atienden|trabajan)\b"
)

ROBOT_PATTERN = re.compile(
    r"\b(robot|bot|humano|humana|persona real|una persona|maquina|inteligencia artificial|ia)\b"
)

# Respuestas que no significan ni "sí" ni "no" para una pregunta sí/no.
BOOL_FILLERS = {
    "ok", "okay", "oki", "no se", "nose", "no lo se", "ni idea",
    "cualquiera", "gracias", "mm", "hmm", "ah", "eh",
}

YES_NO = {"si", "no"}

PREFIXES = {
    "injection": "Solo puedo ayudarte con tu solicitud 🙂",
    "robot": "Soy un asistente virtual con inteligencia artificial; un asesor humano revisará tu caso 🙂",
    "question": "Buena pregunta 🙂 Eso te lo confirma el equipo cuando te contacte.",
    "unclear": "No estoy seguro de haber entendido eso 🤔",
}


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _normalize(message: str) -> str:
    return " ".join(re.sub(r"[^\w\s?]", " ", _fold(message)).split())


def is_yes_no_question(pending_question: dict | None) -> bool:
    options = (pending_question or {}).get("options")

    return bool(options) and all(isinstance(option["value"], bool) for option in options)


def classify_message(message: str, pending_question: dict | None) -> str | None:
    """
    Devuelve por qué este mensaje no debe pasar por la IA (o None si sí):
    "injection", "robot", "question" o "unclear".
    """

    folded = _fold(message).strip()
    normalized = _normalize(message)

    if INJECTION_PATTERN.search(folded):
        return "injection"

    if not re.search(r"[a-z0-9]", folded):
        return "unclear"

    if folded.endswith("?") and QUESTION_START.match(folded.lstrip("¿ ")):
        return "robot" if ROBOT_PATTERN.search(folded) else "question"

    if is_yes_no_question(pending_question):
        if normalized in BOOL_FILLERS or normalized.startswith("no se "):
            return "unclear"
    elif normalized in YES_NO and pending_question:
        return "unclear"

    return None


GREETINGS = {"hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "hola de nuevo"}
ACKNOWLEDGEMENTS = {
    "no", "nada", "nada mas", "gracias", "muchas gracias", "ok", "okay", "vale",
    "perfecto", "genial", "de acuerdo", "entendido", "listo", "si", "claro",
}

SMALLTALK_REPLIES = {
    "greeting": (
        "¡Hola de nuevo! 😊 Ya tengo todos tus datos y el equipo te contactará pronto. "
        "Si tienes alguna duda, dime."
    ),
    "acknowledgement": "¡Perfecto! Si necesitas algo más, aquí estoy 😊",
}


def classify_smalltalk(message: str) -> str | None:
    """
    Saludos y cortesías ("hola", "gracias", "no") una vez completado el
    registro: se contestan con una frase fija en vez de dejar que la IA
    los interprete (pedía el nombre de nuevo o mandaba "comunícalo al equipo").
    """

    normalized = _normalize(message)

    if normalized in GREETINGS:
        return "greeting"

    if normalized in ACKNOWLEDGEMENTS:
        return "acknowledgement"

    return None
