from pydantic import BaseModel


class Case(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None

    nationality: str | None = None
    procedure_type: str | None = None
    current_status: str | None = None

    has_deadline: bool | None = None
    deadline_date: str | None = None

    preferred_date: str | None = None
