from backend.models.lead import Lead
from backend.services.questions import get_next_question
from backend.services.rules import validate_room_rules
from backend.services.matching import find_matching_properties


def process_lead(lead: Lead) -> dict:

    # 1. Comprobar reglas específicas de habitaciones
    if lead.property_type == "habitacion":
        validation = validate_room_rules(lead)

        if not validation["compatible"]:
            return {
                "status": "incompatible",
                "message": "El cliente no cumple los requisitos.",
                "details": validation
            }

    # 2. Comprobar si falta información
    next_question = get_next_question(lead)

    if next_question:
        return {
            "status": "needs_information",
            "question": next_question
        }

    # 3. Buscar propiedades compatibles
    properties = find_matching_properties(lead)

    # 4. Si no encontramos propiedades
    if not properties:
        return {
            "status": "no_results",
            "message": "No encontramos propiedades que coincidan con los criterios."
        }

    # 5. Devolver propiedades encontradas
    return {
        "status": "matches_found",
        "message": "Hemos encontrado propiedades que pueden encajar.",
        "properties": properties
    }