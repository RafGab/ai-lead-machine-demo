from fastapi import APIRouter
from pydantic import BaseModel
from backend.database.database import get_connection

router = APIRouter()


class SearchRequest(BaseModel):
    city: str | None = None
    property_type: str | None = None
    max_price: float | None = None
    bedrooms: int | None = None


@router.post("/search")
def search_properties(request: SearchRequest):
    connection = get_connection()

    query = """
        SELECT *
        FROM properties
        WHERE available = 1
    """

    parameters = []

    if request.city:
        query += " AND city = ?"
        parameters.append(request.city)

    if request.property_type:
        query += " AND property_type = ?"
        parameters.append(request.property_type)

    if request.max_price is not None:
        query += " AND price <= ?"
        parameters.append(request.max_price)

    if request.bedrooms is not None:
        query += " AND bedrooms >= ?"
        parameters.append(request.bedrooms)

    rows = connection.execute(query, parameters).fetchall()

    connection.close()

    return {
        "total": len(rows),
        "results": [dict(row) for row in rows]
    }