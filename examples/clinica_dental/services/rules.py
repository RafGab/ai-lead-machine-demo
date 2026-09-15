from examples.clinica_dental.models.patient import Patient


def evaluate_priority(patient: Patient) -> dict:
    """
    Reglas de negocio propias de la clínica: no filtran al paciente
    (a diferencia de validate_room_rules en el vertical inmobiliario),
    solo deciden cómo se le atiende.
    """

    notes = []

    if patient.is_urgent:
        notes.append(
            "Urgencia: ofrecer el primer hueco disponible, aunque "
            "sea fuera del horario habitual de agenda."
        )

    if patient.specialty == "implantes" and not patient.has_insurance:
        notes.append(
            "Sin seguro + implantes: informar de que es un "
            "tratamiento con presupuesto previo antes de la cita."
        )

    return {
        "priority": "alta" if patient.is_urgent else "normal",
        "notes": notes,
    }
