from backend.models.lead import Lead
from backend.services.normalization import normalize_property_type


def get_next_question(lead: Lead) -> str | None:

    # 1. Operación
    if not lead.operation:
        return "¿Buscas alquilar o comprar?"

    # 2. Tipo de inmueble
    if not lead.property_type:
        return "¿Qué tipo de inmueble estás buscando?"

    # 3. Ciudad
    if not lead.city:
        return "¿En qué ciudad estás buscando?"

    # 4. Presupuesto
    if lead.max_price is None:
        return "¿Cuál es vuestro presupuesto máximo mensual?"

    # 5. Fecha de entrada
    if not lead.move_in_date:
        return "¿Para qué fecha necesitáis entrar?"

    # Ocupantes, menores y mascotas solo importan para habitaciones
    # compartidas (son las únicas reglas que valida rules.py). Para un
    # piso o una casa completa no aplican, así que no se preguntan.
    if normalize_property_type(lead.property_type) == "habitacion":

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