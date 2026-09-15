from examples.asesoria_extranjeria.models.case import Case


def get_next_question(case: Case) -> str | None:

    # 1. Nacionalidad
    if not case.nationality:
        return "¿Cuál es tu nacionalidad?"

    # 2. Tipo de trámite
    if not case.procedure_type:
        return (
            "¿Qué trámite necesitas (residencia, nacionalidad, arraigo, "
            "reagrupación familiar, asilo, recurso, renovación)?"
        )

    # 3. Situación actual
    if not case.current_status:
        return "¿Cuál es tu situación actual (en trámite, sin papeles, con visado...)?"

    # 4. Plazo o fecha límite
    if case.has_deadline is None:
        return "¿Tienes algún plazo o fecha límite para este trámite?"

    if case.has_deadline and not case.deadline_date:
        return "¿Cuál es esa fecha límite?"

    # 5. Fecha preferida para la primera consulta
    if not case.preferred_date:
        return "¿Qué día te vendría bien para la primera consulta con el abogado?"

    return None
