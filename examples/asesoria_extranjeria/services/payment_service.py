import os

import httpx

STRIPE_API_URL = "https://api.stripe.com/v1/checkout/sessions"
FIRST_CONSULTATION_FEE_CENTS = 3000  # 30 €

# Trámites de clientes que están fuera de España y quieren venirse a
# vivir aquí: pagan la consulta inicial de 30 €.
PROCEDURES_REQUIRING_FEE = {
    "residencia inicial",
}

# Trámites administrativos para quien ya está en España: la primera
# consulta es gratuita. (arraigo, reagrupación familiar, asilo,
# nacionalidad y recurso quedan pendientes de confirmar con el cliente
# del despacho — de momento están aquí, en la lista exenta, hasta que
# se aclare.)
PROCEDURES_EXEMPT_FROM_FEE = {
    "renovación",
    "canje de licencia de conducir",
    "modificación de estancia a residencia",
    "arraigo",
    "reagrupación familiar",
    "asilo",
    "nacionalidad",
    "recurso",
}


class PaymentNotConfigured(Exception):
    pass


def requires_first_consultation_fee(procedure_type: str | None) -> bool:
    if not procedure_type:
        return False

    return procedure_type.strip().lower() in PROCEDURES_REQUIRING_FEE


def _get_secret_key() -> str:
    key = os.getenv("STRIPE_SECRET_KEY")

    if not key:
        raise PaymentNotConfigured(
            "STRIPE_SECRET_KEY no está configurado en el archivo .env."
        )

    return key


def create_consultation_checkout(
    case_id: int,
    client_email: str | None,
    success_url: str,
    cancel_url: str,
) -> str:
    """
    Crea una sesión de pago de Stripe Checkout para la primera
    consulta (30 €). Devuelve la URL a la que redirigir al cliente
    para pagar; el número de tarjeta nunca pasa por nuestro backend,
    lo gestiona la página de pago de Stripe.
    """

    secret_key = _get_secret_key()

    payload = {
        "mode": "payment",
        "payment_method_types[0]": "card",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][unit_amount]": str(FIRST_CONSULTATION_FEE_CENTS),
        "line_items[0][price_data][product_data][name]": (
            "Primera consulta - Asesoría de extranjería"
        ),
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata[case_id]": str(case_id),
    }

    if client_email:
        payload["customer_email"] = client_email

    response = httpx.post(
        STRIPE_API_URL,
        headers={"Authorization": f"Bearer {secret_key}"},
        data=payload,
        timeout=10,
    )
    response.raise_for_status()

    return response.json()["url"]


def verify_payment_completed(session_id: str) -> bool:
    """
    Comprueba si una sesión de Checkout se pagó correctamente.

    Se usa desde el webhook checkout.session.completed de Stripe (la
    vía fiable en producción) o al volver del success_url, antes de
    confirmar la cita en el calendario.
    """

    secret_key = _get_secret_key()

    response = httpx.get(
        f"{STRIPE_API_URL}/{session_id}",
        headers={"Authorization": f"Bearer {secret_key}"},
        timeout=10,
    )
    response.raise_for_status()

    return response.json().get("payment_status") == "paid"
