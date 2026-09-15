from pydantic import BaseModel


class Patient(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None

    reason: str | None = None
    specialty: str | None = None
    is_urgent: bool | None = None

    has_insurance: bool | None = None
    insurance_provider: str | None = None

    preferred_date: str | None = None
