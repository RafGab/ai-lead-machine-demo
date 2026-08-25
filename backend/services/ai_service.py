from pydantic import BaseModel


class AILeadData(BaseModel):
    operation: str | None = None
    property_type: str | None = None
    city: str | None = None
    max_price: float | None = None
    move_in_date: str | None = None
    occupants: int | None = None
    has_minors: bool | None = None
    has_pets: bool | None = None


def extract_lead_data(message: str) -> AILeadData:
    """
    Analiza un mensaje del cliente y devuelve
    los datos estructurados del lead.

    Por ahora utilizamos una respuesta simulada.
    Más adelante conectaremos aquí el modelo de IA.
    """

    return AILeadData()