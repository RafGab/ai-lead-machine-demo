from backend.models.lead import Lead


def get_next_question(lead: Lead) -> str | None:

    if not lead.operation:
        return "¿Buscas alquilar o comprar?"

    if not lead.property_type:
        return "¿Qué tipo de inmueble estás buscando?"

    if not lead.city:
        return "¿En qué ciudad estás buscando?"

    if lead.property_type == "habitacion":

        if lead.occupants is None:
            return "¿La habitación sería para una persona o para una pareja?"

        if lead.has_minors is None:
            return "¿Hay algún menor de edad entre las personas que ocuparían la habitación?"

        if lead.has_pets is None:
            return "¿Tenéis alguna mascota?"

    if lead.max_price is None:
        return "¿Cuál es vuestro presupuesto máximo mensual?"

    if not lead.move_in_date:
        return "¿Para qué fecha necesitáis entrar?"

    return None