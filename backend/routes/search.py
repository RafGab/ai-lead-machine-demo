from fastapi import APIRouter
from pydantic import BaseModel
from backend.database.database import get_connection
from backend.services.normalization import normalize_operation, normalize_property_type

router = APIRouter()


class SearchRequest(BaseModel):
    city: str | None = None
    operation: str | None = None
    property_type: str | None = None
    max_price: float | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None


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

    if request.operation:
        query += " AND operation = ?"
        parameters.append(normalize_operation(request.operation))

    if request.property_type:
        query += " AND property_type = ?"
        parameters.append(normalize_property_type(request.property_type))

    if request.max_price is not None:
        query += " AND price <= ?"
        parameters.append(request.max_price)

    if request.bedrooms is not None:
        query += " AND bedrooms >= ?"
        parameters.append(request.bedrooms)

    if request.bathrooms is not None:
        query += " AND bathrooms >= ?"
        parameters.append(request.bathrooms)

    rows = connection.execute(query, parameters).fetchall()

    properties = []

    for row in rows:

        property_data = dict(row)

        images = connection.execute(
            """
            SELECT image_url
            FROM property_images
            WHERE property_id = ?
            """,
            (property_data["id"],)
        ).fetchall()

        property_data["images"] = [
            image["image_url"]
            for image in images
        ]

        properties.append(property_data)

    connection.close()

    return {
        "total": len(properties),
        "results": properties
    }