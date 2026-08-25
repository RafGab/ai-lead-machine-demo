from fastapi import APIRouter
from backend.database.database import get_connection

router = APIRouter()


@router.get("/properties")
def get_properties(
    city: str | None = None,
    property_type: str | None = None,
    max_price: float | None = None,
):
    connection = get_connection()

    query = "SELECT * FROM properties WHERE available = 1"
    parameters = []

    if city:
        query += " AND city = ?"
        parameters.append(city)

    if property_type:
        query += " AND property_type = ?"
        parameters.append(property_type)

    if max_price is not None:
        query += " AND price <= ?"
        parameters.append(max_price)

    rows = connection.execute(query, parameters).fetchall()

    connection.close()

    return [dict(row) for row in rows]