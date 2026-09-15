from backend.models.lead import Lead
from backend.database.database import get_connection
from backend.services.normalization import normalize_operation, normalize_property_type


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

    if lead.operation:
        query += " AND operation = ?"
        parameters.append(normalize_operation(lead.operation))

    if lead.property_type:
        query += " AND property_type = ?"
        parameters.append(normalize_property_type(lead.property_type))

    if lead.max_price is not None:
        query += " AND price <= ?"
        parameters.append(lead.max_price)

    if lead.bedrooms is not None:
        query += " AND bedrooms >= ?"
        parameters.append(lead.bedrooms)

    if lead.bathrooms is not None:
        query += " AND bathrooms >= ?"
        parameters.append(lead.bathrooms)

    rows = connection.execute(query, parameters).fetchall()

    connection.close()

    return [dict(row) for row in rows]