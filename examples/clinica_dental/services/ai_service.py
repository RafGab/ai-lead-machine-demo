import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv(override=True)


class AIPatientData(BaseModel):
    reason: str | None = None
    specialty: str | None = None
    is_urgent: bool | None = None
    has_insurance: bool | None = None
    insurance_provider: str | None = None
    preferred_date: str | None = None


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada en el archivo .env."
        )

    return OpenAI(api_key=api_key)


def extract_patient_data(
    message: str,
    conversation_history: list[dict] | None = None
) -> AIPatientData:
    """
    Utiliza OpenAI para analizar el mensaje del paciente
    teniendo en cuenta el historial de la conversación.
    """

    client = get_openai_client()

    input_messages = [
        {
            "role": "system",
            "content": (
                "Eres el asistente de recepción de una clínica dental.\n\n"

                "Tu única función es recoger los datos necesarios para "
                "agendar una cita: motivo de consulta, si es urgente, "
                "la especialidad, si tiene seguro dental y con qué "
                "compañía, y qué día le vendría bien.\n\n"

                "IMPORTANTE: nunca des consejo médico, ni diagnostiques, "
                "ni valores la gravedad de ningún síntoma. Si el paciente "
                "describe dolor o una urgencia, marca is_urgent=True y "
                "limítate a decir que se le dará prioridad en la agenda; "
                "no opines sobre la causa ni el tratamiento.\n\n"

                "Analiza la conversación y extrae únicamente información "
                "que esté presente o que pueda deducirse claramente. "
                "Si un dato no está presente, devuelve None.\n\n"

                "Para specialty utiliza valores como:\n"
                "- odontología general\n"
                "- ortodoncia\n"
                "- implantes\n"
                "- estética dental\n"
                "- endodoncia\n\n"

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
        text_format=AIPatientData,
    )

    return response.output_parsed
