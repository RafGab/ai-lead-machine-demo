from examples.clinica_dental.models.patient import Patient


def get_next_question(patient: Patient) -> str | None:

    # 1. Motivo de consulta
    if not patient.reason:
        return "¿Cuál es el motivo de tu consulta?"

    # 2. Urgencia
    if patient.is_urgent is None:
        return "¿Es urgente? ¿Tienes dolor ahora mismo?"

    # 3. Especialidad
    if not patient.specialty:
        return "¿Qué tipo de consulta necesitas (general, ortodoncia, implantes, estética)?"

    # 4. Seguro dental
    if patient.has_insurance is None:
        return "¿Tienes seguro dental?"

    if patient.has_insurance and not patient.insurance_provider:
        return "¿Con qué compañía de seguro dental?"

    # 5. Fecha preferida
    if not patient.preferred_date:
        return "¿Qué día te vendría bien para la cita?"

    return None
