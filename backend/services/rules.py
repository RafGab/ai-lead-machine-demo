from backend.models.lead import Lead


def validate_room_rules(lead: Lead) -> dict:

    violations = []

    if lead.has_minors is True:
        violations.append(
            "No se admiten menores de edad."
        )

    if lead.has_pets is True:
        violations.append(
            "No se admiten mascotas."
        )

    if lead.occupants is not None and lead.occupants not in [1, 2]:
        violations.append(
             "La habitación es para una persona o una pareja."
    
        )

    if violations:
        return {
            "compatible": False,
            "violations": violations
        }

    return {
        "compatible": True,
        "violations": []
    }