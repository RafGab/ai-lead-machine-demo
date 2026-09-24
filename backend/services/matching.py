import math

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


def get_available_cities() -> list[str]:
    connection = get_connection()

    cities = [
        row["city"]
        for row in connection.execute(
            "SELECT DISTINCT city FROM properties WHERE available = 1 ORDER BY city"
        ).fetchall()
    ]

    connection.close()

    return cities


def explain_no_matches(lead: Lead) -> dict:
    """
    Cuando no hay resultados, explica el motivo más probable en vez
    de un mensaje genérico, para que el cliente sepa qué ajustar.

    Devuelve {"message", "options", "options_field"}: las opciones son
    botones de respuesta rápida para que un "sí" ambiguo no deje la
    conversación atascada repitiendo la misma pregunta.
    """

    retry_city = {"label": "Probar otra ciudad", "value": "city"}
    retry_budget = {"label": "Ampliar el presupuesto", "value": "budget"}

    connection = get_connection()

    if lead.city:
        city_has_properties = connection.execute(
            "SELECT COUNT(*) FROM properties WHERE city = ? AND available = 1",
            (lead.city,),
        ).fetchone()[0]

        if city_has_properties == 0:
            connection.close()
            available_cities = get_available_cities()

            return {
                "message": (
                    f"Todavía no tenemos propiedades en {lead.city}. "
                    f"Por ahora trabajamos en: {', '.join(available_cities)}. "
                    "¿Quieres probar con alguna de estas ciudades?"
                ),
                "options": [{"label": city, "value": city} for city in available_cities],
                "options_field": "city",
            }

    price_query = "SELECT MIN(price) FROM properties WHERE available = 1"
    price_parameters = []

    if lead.city:
        price_query += " AND city = ?"
        price_parameters.append(lead.city)

    if lead.operation:
        price_query += " AND operation = ?"
        price_parameters.append(normalize_operation(lead.operation))

    if lead.property_type:
        price_query += " AND property_type = ?"
        price_parameters.append(normalize_property_type(lead.property_type))

    min_price = connection.execute(price_query, price_parameters).fetchone()[0]

    connection.close()

    if min_price is not None and lead.max_price is not None and min_price > lead.max_price:
        return {
            "message": (
                f"Con ese presupuesto no encontramos nada en {lead.city or 'esa ciudad'}: "
                f"lo más económico disponible ahí es de {min_price:.0f} €. "
                "¿Quieres ampliar el presupuesto o probar otra ciudad?"
            ),
            "options": [
                {"label": f"Subir a {min_price:.0f} €", "value": f"raise:{math.ceil(min_price)}"},
                retry_budget,
                retry_city,
            ],
            "options_field": "_retry",
        }

    return {
        "message": (
            "No encontramos propiedades que coincidan con todos los criterios. "
            "¿Quieres ajustar la ciudad o el presupuesto?"
        ),
        "options": [retry_city, retry_budget],
        "options_field": "_retry",
    }