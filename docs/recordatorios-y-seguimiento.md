# Recordatorios de cita y seguimiento automático

Dos funciones que escriben **por correo** al cliente final. Están **apagadas por defecto**.
Solo afectan a las conversaciones que llegan desde la web real de un cliente (`source = widget`), nunca a la demo.

## Qué hace

**Recordatorio de cita.** Un correo al cliente unas horas antes de su cita (por defecto 24 h antes).
- Solo si reservó con suficiente antelación: una cita hecha con menos de 24 h de margen no recibe un recordatorio "de 24 h" nada más reservar.
- Con `REMINDER_HOURS_BEFORE=24,2` manda también uno 2 h antes. Si se perdió una ventana (por ejemplo el servidor estuvo parado), no la envía tarde.
- El correo sale con el nombre del negocio y, en "Responder", el `COMERCIAL_EMAIL` de ese rubro, para que el cliente pueda cambiar o cancelar la cita.

**Seguimiento.** A quien dejó su correo y no agendó ni pidió hablar con una persona:
- 1.er mensaje tras 24 h sin actividad, 2.º tras 72 h (`FOLLOWUP_AFTER_HOURS=24,72`). Como máximo dos.
- Solo si el lead sigue en estado **"nuevo"** en el panel. Pasarlo a "contactado" o "cerrado" detiene el seguimiento.
- Lleva enlace de baja firmado; si alguien responde "BAJA", el negocio lo apunta con `POST /admin/reminders/optout`.

## Cómo activarlo (por cliente)

1. En Render, variables de entorno del servicio de ese cliente:

| Variable | Para qué | Por defecto |
|---|---|---|
| `REMINDERS_ENABLED` | `1` para activar | `0` |
| `SMTP_USER`, `SMTP_PASSWORD` | Cuenta Gmail que envía (contraseña de aplicación) | ya existentes |
| `PUBLIC_BASE_URL` | URL pública del backend, para el enlace de baja | — |
| `SITE_URL` (o `SITE_URL_<RUBRO>`) | Web del negocio, para el "retómalo cuando quieras" | — |
| `BUSINESS_NAME` (o `BUSINESS_NAME_<RUBRO>`) | Nombre que firma los correos | nombre del rubro |
| `COMERCIAL_EMAIL` (o `COMERCIAL_EMAIL_<RUBRO>`) | "Responder a" de los correos | ya existente |
| `REMINDER_HOURS_BEFORE` | Horas antes de la cita, separadas por comas | `24` |
| `FOLLOWUP_AFTER_HOURS` | Horas de inactividad de cada seguimiento | `24,72` |
| `FOLLOWUP_MAX_AGE_DAYS` | No seguir leads más antiguos que esto | `7` |
| `REMINDER_INTERVAL_MINUTES` | Cada cuánto revisa | `15` |
| `REMINDERS_SOURCES` | Orígenes que se incluyen | `widget` |

2. **Antes de activarlo de verdad, ve qué se enviaría** (no envía nada):
   `POST https://TU-BACKEND/admin/reminders/run?key=TU_ADMIN_KEY` (por defecto es una vista previa).
3. Activa `REMINDERS_ENABLED=1` y reinicia. El seguimiento **solo mira conversaciones posteriores al momento de activarlo**,
   para no escribir de golpe a todos los leads antiguos.

## Garantías

- **Nunca se repite un correo:** cada envío se reserva en la base de datos antes de hacerlo (clave primaria). Si el envío falla, se libera y se reintenta en el siguiente repaso, sin tocar lo que ya se envió.
- **Sin ráfagas** al activarlo, como se explica arriba.
- **Baja respetada** en los seguimientos. Los recordatorios de una cita que la persona misma reservó son transaccionales y no la respetan.
- Si falta `SMTP_USER` o `SMTP_PASSWORD`, no envía nada y lo indica.

## Antes de activarlo en un negocio real (importante)

- **Privacidad (RGPD en España, Ley 1581 en Colombia):** el seguimiento es una comunicación adicional al correo que el cliente dejó.
  El widget **todavía no muestra un aviso** que lo anuncie. Añade en el chat o en la política de privacidad del cliente una frase
  del tipo "Podemos escribirte por correo para recordarte tu cita y hacer seguimiento de tu consulta".
- **Solo correo.** No hay WhatsApp ni SMS: el agente aún no los tiene.
- **Un solo proceso:** el revisor corre dentro de la web. Con el plan starter de Render (una instancia) es lo correcto.
  Con varias instancias no se duplican correos, pero cada una haría el repaso.
- Gmail limita los envíos diarios de una cuenta personal; para volúmenes altos usa un proveedor transaccional.

## Archivos

- `backend/demo/reminders.py`: la lógica, el revisor y el arranque.
- `backend/demo/reminders_routes.py`: baja, vista previa y ejecución manual.
- `backend/services/notify.py`: `send_email` (envío síncrono que informa si salió).
- `tests/test_reminders.py`: 22 pruebas.
