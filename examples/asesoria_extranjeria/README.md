# Ejemplo: mismo motor aplicado a una asesoría de extranjería

Mismo patrón que `examples/clinica_dental/`, con una pieza nueva: el pago
de 30 € de la primera consulta, que **no siempre aplica**.

## Regla de negocio: ¿cuándo se cobran los 30 €?

Solo en la primera reunión de alguien que está **fuera de España y quiere
venirse a vivir aquí**. Los trámites para quien **ya está en España**
(canje de licencia de conducir, modificar de estancia a residencia,
renovaciones) no pagan.

Esa regla vive en un único sitio fácil de ajustar,
[`services/payment_service.py`](services/payment_service.py):

```python
PROCEDURES_REQUIRING_FEE = {"residencia inicial"}
PROCEDURES_EXEMPT_FROM_FEE = {
    "renovación", "canje de licencia de conducir",
    "modificación de estancia a residencia",
    "arraigo", "reagrupación familiar", "asilo", "nacionalidad", "recurso",
}
```

**Importante — te lo dejo marcado en el propio código:** confirmaste que
canje de conducir, modificar estancia→residencia y renovación no pagan, y
que la primera consulta de alguien que quiere migrar sí paga. Pero
arraigo, reagrupación familiar, asilo, nacionalidad y recurso son casos
donde el cliente puede estar dentro o fuera de España según cada
situación — de momento los dejé como exentos por defecto (para no cobrar
de más por error) hasta que me confirmes cada uno.

## Se sustituyen / se añaden

| Archivo | Qué es |
|---|---|
| `models/case.py` | Nacionalidad, trámite, situación actual, plazo — en vez de campos inmobiliarios |
| `services/ai_service.py` | Prompt adaptado + regla explícita: nunca dar asesoramiento legal, solo recoger datos |
| `services/questions.py` | Orden de preguntas del despacho |
| `services/rules.py` | Prioriza casos con plazo límite |
| `services/payment_service.py` | **Nuevo**: crea la sesión de pago en Stripe Checkout (30 €) y comprueba si se pagó. El número de tarjeta nunca pasa por nuestro backend, lo gestiona la página de Stripe. |
| `services/case_service.py` | **Nuevo**: decide si el trámite requiere pago antes de agendar. Si no lo requiere, agenda directo (como en inmobiliaria/clínica). Si lo requiere, primero manda al cliente a pagar y solo agenda cuando Stripe confirma el pago. |

## Se reutiliza sin tocar una línea

- `backend/services/calendar_service.py` — `case_service.py` lo importa
  directamente para comprobar disponibilidad y crear el evento; es la
  misma función que usa la inmobiliaria para las visitas.
- `conversation_repository.py`, `conversation_service.py`, rutas y widget
  — igual que en el ejemplo de la clínica dental.

## Flujo con pago

1. El cliente completa los datos del caso en el chat/widget.
2. Al llegar a la fecha preferida, `schedule_case_meeting()` decide:
   - **Trámite exento** → agenda directo, como cualquier otra visita/cita.
   - **Trámite con coste** → crea una sesión de Stripe Checkout y devuelve
     la URL de pago; todavía no se toca el calendario.
3. El cliente paga en la página de Stripe (fuera de nuestra web).
4. Stripe confirma el pago (webhook `checkout.session.completed`, la vía
   fiable en producción, o el `success_url` al volver). Solo entonces
   `confirm_paid_meeting()` comprueba el pago y agenda la cita real.

Esto evita el problema típico de cobrar y no agendar (o agendar sin
cobrar) si el cliente cierra la pestaña a mitad del pago: la cita solo
se crea después de que Stripe confirme, nunca antes.

## Para activarlo de verdad

Hace falta una cuenta de Stripe y añadir en `.env`:

```
STRIPE_SECRET_KEY=sk_live_...   (o sk_test_... mientras pruebas)
```

(Documentado también en `.env.example` en la raíz del proyecto.)
