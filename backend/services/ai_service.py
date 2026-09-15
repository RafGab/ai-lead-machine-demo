import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv(override=True)


class AILeadData(BaseModel):
    operation: str | None = None
    property_type: str | None = None
    city: str | None = None
    max_price: float | None = None
    move_in_date: str | None = None
    occupants: int | None = None
    has_minors: bool | None = None
    has_pets: bool | None = None


def get_openai_client() -> OpenAI:
    """
    Crea el cliente de OpenAI utilizando la API key
    almacenada en el archivo .env.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada en el archivo .env."
        )

    return OpenAI(api_key=api_key)


def extract_lead_data(
    message: str,
    conversation_history: list[dict] | None = None
) -> AILeadData:
    """
    Utiliza OpenAI para analizar el mensaje del cliente
    teniendo en cuenta el historial de la conversación.
    """

    client = get_openai_client()

    input_messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente especializado en captación "
                "de leads inmobiliarios.\n\n"

                "Analiza la conversación y extrae únicamente "
                "información que esté presente o que pueda "
                "deducirse claramente.\n\n"

                "No inventes información.\n"
                "Si un dato no está presente, devuelve None.\n\n"

                "Para operation utiliza únicamente:\n"
                "- alquiler\n"
                "- compra\n\n"

                "Para property_type utiliza valores como:\n"
                "- vivienda\n"
                "- piso\n"
                "- apartamento\n"
                "- casa\n"
                "- chalet\n"
                "- habitacion\n\n"

                "Si el cliente indica que NO tiene menores, "
                "has_minors debe ser False.\n"

                "Si el cliente indica que NO tiene mascotas, "
                "has_pets debe ser False.\n"

                "Si el cliente indica que sí tiene menores, "
                "has_minors debe ser True.\n"

                "Si el cliente indica que sí tiene mascotas, "
                "has_pets debe ser True.\n\n"

                "Para occupants utiliza el número de personas "
                "que vivirán en el inmueble cuando esté indicado.\n\n"

                "MUY IMPORTANTE: interpreta las respuestas "
                "cortas como 'sí' o 'no' teniendo en cuenta "
                "la pregunta inmediatamente anterior."
            ),
        }
    ]

    if conversation_history:
        for item in conversation_history:
            input_messages.append(
                {
                    "role": item["role"],
                    "content": item["content"],
                }
            )

    input_messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    response = client.responses.parse(
        model="gpt-4o-mini",
        input=input_messages,
        text_format=AILeadData,
    )

    return response.output_parsed