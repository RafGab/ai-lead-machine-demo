from examples.asesoria_extranjeria.models.case import Case


def evaluate_priority(case: Case) -> dict:
    """
    Igual que en la clínica dental: no filtra al cliente, decide
    cómo se le atiende.
    """

    notes = []

    if case.has_deadline:
        notes.append(
            "Tiene un plazo límite: ofrecer la primera cita disponible "
            "y avisar al abogado antes de la consulta."
        )

    if case.procedure_type == "asilo":
        notes.append(
            "Solicitud de asilo: revisar si aplica alguna vía de "
            "urgencia antes de la cita."
        )

    return {
        "priority": "alta" if case.has_deadline else "normal",
        "notes": notes,
    }
