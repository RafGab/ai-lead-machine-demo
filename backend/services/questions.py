from datetime import datetime, timedelta

from backend.models.lead import Lead
from backend.services.normalization import normalize_operation, normalize_property_type
from backend.services.matching import get_available_cities


def _option(label: str, value) -> dict:
    return {"label": label, "value": value}


def get_next_question(lead: Lead) -> dict | None:
    """
    Devuelve la siguiente pregunta como
    {"text": ..., "field": ..., "options": ...}.

    "field" es el campo del Lead que responde esta pregunta.
    "options" es una lista de {label, value} para respuestas rápidas
    en preguntas de catálogo cerrado: al pulsar una, el valor se
    guarda directamente (sin pasar por la IA), así que nunca puede
    "malinterpretarse". None en preguntas abiertas (presupuesto...)
    donde solo tiene sentido escribir y sí pasa por la IA. El cliente
    siempre puede escribir en vez de tocar un botón.
    """

    # 1. Operación
    if not lead.operation:
        return {
            "text": "¿Buscas alquilar o comprar?",
            "field": "operation",
            "options": [
                _option("Alquilar", "alquiler"),
                _option("Comprar", "compra"),
            ],
        }

    normalized_operation = normalize_operation(lead.operation)

    # 2. Tipo de inmueble
    if not lead.property_type:
        return {
            "text": "¿Qué tipo de inmueble estás buscando?",
            "field": "property_type",
            "options": [
                _option("Piso o casa", "vivienda"),
                _option("Habitación", "habitacion"),
            ],
        }

    normalized_type = normalize_property_type(lead.property_type)

    # 3. Ciudad
    if not lead.city:
        return {
            "text": "¿En qué ciudad estás buscando?",
            "field": "city",
            "options": [_option(city, city) for city in get_available_cities()],
        }

    # 4. Presupuesto (abierto: no tiene sentido como botones)
    if lead.max_price is None:
        if normalized_operation == "venta":
            return {"text": "¿Cuál es tu presupuesto máximo?", "field": "max_price", "options": None}

        return {
            "text": "¿Cuál es vuestro presupuesto máximo mensual?",
            "field": "max_price",
            "options": None,
        }

    # 5. Fecha de entrada
    if not lead.move_in_date:
        today = datetime.now()
        next_month = today.replace(day=1) + timedelta(days=32)

        return {
            "text": "¿Para qué fecha necesitáis entrar?",
            "field": "move_in_date",
            "options": [
                _option("Lo antes posible", today.strftime("%m-%Y")),
                _option("El próximo mes", next_month.strftime("%m-%Y")),
                _option("Sin prisa, solo estoy mirando", "sin fecha definida"),
            ],
        }

    # Ocupantes, menores y mascotas: siempre importan en habitaciones
    # compartidas (son las reglas que valida rules.py). En un piso o
    # casa completa en alquiler también importan (algunos propietarios
    # no admiten mascotas o menores), pero no en una compra.
    if normalized_type == "habitacion":

        # 6. Número de ocupantes
        if lead.occupants is None:
            return {
                "text": "¿Cuántas personas vivirían en el inmueble?",
                "field": "occupants",
                "options": [_option("1 persona", 1), _option("2 personas", 2)],
            }

        # 7. Menores
        if lead.has_minors is None:
            return {
                "text": "¿Hay algún menor de edad entre las personas que vivirían allí?",
                "field": "has_minors",
                "options": [_option("Sí", True), _option("No", False)],
            }

        # 8. Mascotas
        if lead.has_pets is None:
            return {
                "text": "¿Tenéis alguna mascota?",
                "field": "has_pets",
                "options": [_option("Sí", True), _option("No", False)],
            }

        return None

    if normalized_operation == "alquiler":

        # 6. Menores
        if lead.has_minors is None:
            return {
                "text": "¿Hay algún menor de edad entre las personas que vivirían allí?",
                "field": "has_minors",
                "options": [_option("Sí", True), _option("No", False)],
            }

        # 7. Mascotas
        if lead.has_pets is None:
            return {
                "text": (
                    "¿Tenéis alguna mascota? Algunos propietarios no las admiten, "
                    "así que nos ayuda a filtrar mejor."
                ),
                "field": "has_pets",
                "options": [_option("Sí", True), _option("No", False)],
            }

        return None

    if normalized_operation == "venta":

        # 6. Habitaciones
        if lead.bedrooms is None:
            return {
                "text": "¿Cuántas habitaciones necesitas?",
                "field": "bedrooms",
                "options": [
                    _option("1", 1), _option("2", 2), _option("3", 3), _option("4 o más", 4),
                ],
            }

        # 7. Baños
        if lead.bathrooms is None:
            return {
                "text": "¿Cuántos baños necesitas?",
                "field": "bathrooms",
                "options": [_option("1", 1), _option("2", 2), _option("3 o más", 3)],
            }

        return None

    return None
