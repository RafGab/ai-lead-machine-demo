from backend.models.lead import Lead
from backend.database.database import get_connection


def find_matching_properties(lead: Lead) -> list[dict]:

    connection = get_connection()

    query = """
        SELECT *
        FROM properties
        WHERE available = 1
    """

    parameters = []

    if lead.city:
        query += " AND city = ?"
        parameters.append(lead.city)

    if lead.property_type:
       property_type_map = {
        "piso": "vivienda",
        "apartamento": "vivienda",
        "casa": "vivienda",
        "chalet": "vivienda",
        "vivienda": "vivienda",
        "habitacion": "habitacion",
    }

       normalized_property_type = property_type_map.get(
        lead.property_type.lower(),
        lead.property_type.lower()
    )

       query += " AND property_type = ?"
       parameters.append(normalized_property_type)

    if lead.max_price is not None:
        query += " AND price <= ?"
        parameters.append(lead.max_price)

    rows = connection.execute(query, parameters).fetchall()

    connection.close()

    return [dict(row) for row in rows]