from backend.models.lead import Lead
from backend.services.normalization import normalize_operation, normalize_property_type


def get_next_question(lead: Lead) -> str | None:

    # 1. Operación
    if not lead.operation:
        return "¿Buscas alquilar o comprar?"

    normalized_operation = normalize_operation(lead.operation)

    # 2. Tipo de inmueble
    if not lead.property_type:
        return "¿Qué tipo de inmueble estás buscando?"

    normalized_type = normalize_property_type(lead.property_type)

    # 3. Ciudad
    if not lead.city:
        return "¿En qué ciudad estás buscando?"

    # 4. Presupuesto
    if lead.max_price is None:
        if normalized_operation == "venta":
            return "¿Cuál es tu presupuesto máximo?"

        return "¿Cuál es vuestro presupuesto máximo mensual?"

    # 5. Fecha de entrada
    if not lead.move_in_date:
        return "¿Para qué fecha necesitáis entrar?"

    # Ocupantes, menores y mascotas: siempre importan en habitaciones
    # compartidas (son las reglas que valida rules.py). En un piso o
    # casa completa en alquiler también importan (algunos propietarios
    # no admiten mascotas o menores), pero no en una compra.
    if normalized_type == "habitacion":

        # 6. Número de ocupantes
        if lead.occupants is None:
            return "¿Cuántas personas vivirían en el inmueble?"

        # 7. Menores
        if lead.has_minors is None:
            return "¿Hay algún menor de edad entre las personas que vivirían allí?"

        # 8. Mascotas
        if lead.has_pets is None:
            return "¿Tenéis alguna mascota?"

        return None

    if normalized_operation == "alquiler":

        # 6. Menores
        if lead.has_minors is None:
            return "¿Hay algún menor de edad entre las personas que vivirían allí?"

        # 7. Mascotas
        if lead.has_pets is None:
            return (
                "¿Tenéis alguna mascota? Algunos propietarios no las admiten, "
                "así que nos ayuda a filtrar mejor."
            )

        return None

    if normalized_operation == "venta":

        # 6. Habitaciones
        if lead.bedrooms is None:
            return "¿Cuántas habitaciones necesitas?"

        # 7. Baños
        if lead.bathrooms is None:
            return "¿Cuántos baños necesitas?"

        return None

    return None
