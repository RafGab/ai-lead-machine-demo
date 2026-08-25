from pydantic import BaseModel


class Lead(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None

    operation: str | None = None
    property_type: str | None = None
    city: str | None = None
    max_price: float | None = None

    move_in_date: str | None = None
    bedrooms: int | None = None
    area: str | None = None
    occupants: int | None = None

    has_minors: bool | None = None
    has_pets: bool | None = None

    employment_status: str | None = None
    documentation_ready: bool | None = None