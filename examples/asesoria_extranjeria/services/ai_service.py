import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv(override=True)


class AICaseData(BaseModel):
    nationality: str | None = None
    procedure_type: str | None = None
    current_status: str | None = None
    has_deadline: bool | None = None
    deadline_date: str | None = None
    preferred_date: str | None = None


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada en el archivo .env."
        )

    return OpenAI(api_key=api_key)


def extract_case_data(
    message: str,
    conversation_history: list[dict] | None = None
) -> AICaseData:
    """
    Utiliza OpenAI para analizar el mensaje del cliente y extraer
    los datos de su caso, teniendo en cuenta el historial.
    """

    client = get_openai_client()

    input_messages = [
        {
            "role": "system",
            "content": (
                "Eres el asistente de recepción de una asesoría de "
                "extranjería.\n\n"

                "Tu única función es recoger los datos necesarios para "
                "agendar una primera consulta: nacionalidad, tipo de "
                "trámite, situación actual, si hay algún plazo o fecha "
                "límite, y qué día le vendría bien para la cita.\n\n"

                "IMPORTANTE: nunca des asesoramiento legal, ni valores "
                "la viabilidad del caso, ni prometas resultados ni "
                "plazos de resolución. Eso solo lo puede hacer el "
                "abogado en la consulta. Si el cliente pregunta algo "
                "legal, indica que el abogado se lo explicará en la "
                "cita.\n\n"

                "Analiza la conversación y extrae únicamente información "
                "que esté presente o que pueda deducirse claramente. "
                "Si un dato no está presente, devuelve None.\n\n"

                "Para procedure_type utiliza valores como:\n"
                "- residencia inicial (cliente fuera de España que quiere venirse a vivir aquí)\n"
                "- nacionalidad\n"
                "- arraigo\n"
                "- reagrupación familiar\n"
                "- asilo\n"
                "- recurso\n"
                "- renovación\n"
                "- canje de licencia de conducir\n"
                "- modificación de estancia a residencia\n\n"

                "Para current_status utiliza valores como:\n"
                "- en trámite\n"
                "- situación irregular\n"
                "- con visado\n"
                "- recurso denegado\n\n"

                "MUY IMPORTANTE: interpreta las respuestas cortas como "
                "'sí' o 'no' teniendo en cuenta la pregunta inmediatamente "
                "anterior."
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
        text_format=AICaseData,
    )

    return response.output_parsed
