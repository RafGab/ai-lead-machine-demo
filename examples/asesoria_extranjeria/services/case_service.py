from backend.services.calendar_service import (
    CalendarNotConfigured,
    create_visit_event,
    is_slot_available,
    suggest_alternative_slots,
)

from examples.asesoria_extranjeria.services.payment_service import (
    create_consultation_checkout,
    requires_first_consultation_fee,
    verify_payment_completed,
)

# La disponibilidad y el calendario se reutilizan sin cambiar una
# línea de backend/services/calendar_service.py: una cita con el
# abogado se comprueba y se agenda exactamente igual que una visita
# a un piso.


def schedule_case_meeting(
    case_id: int,
    procedure_type: str | None,
    scheduled_at: str,
    client_name: str | None,
    client_email: str | None,
    success_url: str,
    cancel_url: str,
) -> dict:
    """
    Punto de entrada al agendar la primera consulta.

    Si el trámite requiere el pago de 30 €, no agenda nada todavía:
    devuelve la URL de pago de Stripe y la cita se confirma en
    confirm_paid_meeting() cuando el pago se completa. Si el trámite
    está exento, agenda directamente (mismo flujo que en inmobiliaria
    o en la clínica dental).
    """

    if requires_first_consultation_fee(procedure_type):
        checkout_url = create_consultation_checkout(
            case_id=case_id,
            client_email=client_email,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        return {
            "requires_payment": True,
            "checkout_url": checkout_url,
            "message": (
                "La primera consulta para este trámite tiene un coste "
                "de 30 €. Te hemos enviado al pago seguro; en cuanto "
                "se confirme, la cita queda agendada."
            ),
        }

    return _book_meeting(scheduled_at, client_name, client_email, procedure_type)


def confirm_paid_meeting(
    session_id: str,
    scheduled_at: str,
    client_name: str | None,
    client_email: str | None,
    procedure_type: str | None,
) -> dict:
    """
    Se llama desde el webhook checkout.session.completed de Stripe
    (o al volver del success_url) para confirmar el pago antes de
    tocar el calendario del abogado.
    """

    if not verify_payment_completed(session_id):
        return {
            "booked": False,
            "message": "El pago todavía no se ha confirmado.",
        }

    return _book_meeting(scheduled_at, client_name, client_email, procedure_type)


def _book_meeting(
    scheduled_at: str,
    client_name: str | None,
    client_email: str | None,
    procedure_type: str | None,
) -> dict:
    try:
        available = is_slot_available(scheduled_at)
    except CalendarNotConfigured:
        available = None

    if available is False:
        return {
            "booked": False,
            "message": "Esa hora ya está ocupada para el abogado.",
            "alternative_slots": suggest_alternative_slots(scheduled_at),
        }

    event_id = None

    try:
        event_id = create_visit_event(
            property_title=f"Primera consulta ({procedure_type or 'trámite'})",
            property_city="Despacho",
            scheduled_at=scheduled_at,
            lead_name=client_name,
            lead_phone=None,
            lead_email=client_email,
        )
    except CalendarNotConfigured:
        pass

    return {
        "booked": True,
        "calendar_event_id": event_id,
        "message": "Cita confirmada con el abogado.",
    }
