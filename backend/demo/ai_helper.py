import os

from dotenv import load_dotenv
from openai import OpenAI

from backend.services.sanitize import EXTRACTION_RULES

load_dotenv(override=True)


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no está configurada en el archivo .env.")

    return OpenAI(api_key=api_key)


def call_ai(system_prompt: str, model_cls, message: str, conversation_history: list[dict] | None = None):
    """
    Boilerplate compartido por todos los verticales de la demo: arma
    los mensajes de entrada y llama a OpenAI con extracción
    estructurada. temperature=0 para respuestas deterministas.
    """

    client = get_openai_client()

    input_messages = [{"role": "system", "content": system_prompt + EXTRACTION_RULES}]

    if conversation_history:
        for item in conversation_history:
            input_messages.append({"role": item["role"], "content": item["content"]})

    input_messages.append({"role": "user", "content": message})

    response = client.responses.parse(
        model="gpt-4o-mini",
        input=input_messages,
        text_format=model_cls,
        temperature=0,
    )

    return response.output_parsed


def option(label: str, value) -> dict:
    """Respuesta rápida de botón: {label, value}, igual que en inmobiliaria."""
    return {"label": label, "value": value}


FOLLOWUP_REMINDER = (
    "Recordatorio final: el registro de esta persona ya está COMPLETO. Responde solo a lo "
    "último que dijo, sin volver a pedir datos, sin saludar como si empezara la conversación "
    "y sin repetir tu presentación. Nunca digas que has actualizado, cambiado, cancelado o "
    "reservado nada: no tienes esa capacidad. SOLO si pide expresamente un cambio "
    "(teléfono, cita, datos) o cancelar, dile que se lo comunique al equipo cuando le "
    "contacten; en cualquier otro caso responde a lo que pregunta."
)


def generate_followup_reply(
    context_prompt: str,
    message: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Respuesta conversacional libre (no extracción estructurada) para
    cuando el cliente pregunta algo después de completar su registro.
    """

    client = get_openai_client()

    input_messages = [{"role": "system", "content": context_prompt}]

    if conversation_history:
        for item in conversation_history:
            input_messages.append({"role": item["role"], "content": item["content"]})

    input_messages.append({"role": "system", "content": FOLLOWUP_REMINDER})
    input_messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=input_messages,
        temperature=0.4,
        max_tokens=220,
    )

    return response.choices[0].message.content.strip()
