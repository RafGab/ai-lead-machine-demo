"""
Recordatorios de cita y seguimiento automático, por correo.

Dos funciones, ambas pensadas para las webs reales de los clientes
(source = "widget") y APAGADAS por defecto (REMINDERS_ENABLED):

1. Recordatorio de cita: un correo al cliente unas horas antes de su cita
   (REMINDER_HOURS_BEFORE, por defecto 24). Solo si reservó con suficiente
   antelación: una cita hecha con menos de 24 h de margen no recibe un
   recordatorio "de 24 h" justo después de reservar.

2. Seguimiento: a quien dejó su correo, no agendó ni pidió hablar con una
   persona y sigue en estado "nuevo" en el panel de leads, se le escribe
   tras FOLLOWUP_AFTER_HOURS de inactividad (por defecto 24 y 72 h, como
   máximo dos mensajes). Pasar el lead a "contactado" o "cerrado" en el
   panel detiene el seguimiento.

Garantías para no molestar al cliente del cliente:
- Nunca se repite un mensaje: se "reclama" en la base de datos antes de
  enviarlo (clave primaria), y si el envío falla se libera para reintentar.
- Nada de ráfagas al activarlo: el seguimiento solo mira conversaciones
  posteriores al momento en que se activó por primera vez.
- Los correos de seguimiento llevan enlace de baja, que se respeta.
"""

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

from backend.database.database import get_connection
from backend.demo.verticals import vertical_label
from backend.services.notify import send_email, smtp_configured
from backend.services.sanitize import is_valid_email

logger = logging.getLogger(__name__)

UTC = timezone.utc
DB_TIME = "%Y-%m-%d %H:%M:%S"

DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# No se envía un recordatorio si faltan menos de estos minutos para la cita.
MIN_LEAD = timedelta(minutes=30)


# ---------------------------------------------------------------- configuración

def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "si", "sí", "on")


def enabled() -> bool:
    return _flag("REMINDERS_ENABLED")


def _int_list(name: str, default: list[int]) -> list[int]:
    raw = os.getenv(name, "")
    values = []

    for part in raw.split(","):
        part = part.strip()

        if part.isdigit() and int(part) > 0:
            values.append(int(part))

    return sorted(set(values)) or default


def reminder_hours() -> list[int]:
    return _int_list("REMINDER_HOURS_BEFORE", [24])


def followup_hours() -> list[int]:
    return _int_list("FOLLOWUP_AFTER_HOURS", [24, 72])


def followup_max_age() -> timedelta:
    days = os.getenv("FOLLOWUP_MAX_AGE_DAYS", "7")

    return timedelta(days=int(days) if days.isdigit() and int(days) > 0 else 7)


def sources() -> list[str]:
    raw = os.getenv("REMINDERS_SOURCES", "widget")

    return [part.strip() for part in raw.split(",") if part.strip()] or ["widget"]


def _timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Madrid"))


def business_name(vertical: str) -> str:
    return (
        os.getenv(f"BUSINESS_NAME_{vertical.upper()}")
        or os.getenv("BUSINESS_NAME")
        or vertical_label(vertical)
    )


def reply_to_for(vertical: str) -> str | None:
    for name in (
        f"COMERCIAL_EMAIL_{vertical.upper()}", "COMERCIAL_EMAIL",
        f"NOTIFY_EMAIL_{vertical.upper()}", "NOTIFY_EMAIL",
    ):
        if os.getenv(name):
            return os.getenv(name)

    return None


def site_url_for(vertical: str) -> str | None:
    return os.getenv(f"SITE_URL_{vertical.upper()}") or os.getenv("SITE_URL")


# ---------------------------------------------------------------------- tablas

def create_tables() -> None:
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_reminders_sent (
            appointment_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (appointment_id, kind)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_followups_sent (
            conversation_id INTEGER NOT NULL,
            step INTEGER NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (conversation_id, step)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_email_optouts (
            email TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS demo_reminder_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def _enabled_since(connection, now: datetime, persist: bool) -> datetime:
    """Momento en que se activó por primera vez (se fija en la primera ejecución)."""

    row = connection.execute(
        "SELECT value FROM demo_reminder_settings WHERE key = 'enabled_since'"
    ).fetchone()

    if row is not None:
        return _parse_db_time(row["value"])

    if persist:
        connection.execute(
            "INSERT OR IGNORE INTO demo_reminder_settings (key, value) VALUES ('enabled_since', ?)",
            (now.astimezone(UTC).strftime(DB_TIME),),
        )
        connection.commit()

    return now


# ------------------------------------------------------------------- utilidades

def _parse_db_time(value: str) -> datetime:
    return datetime.strptime(value[:19], DB_TIME).replace(tzinfo=UTC)


def _parse_appointment(scheduled_at: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(scheduled_at)
    except (TypeError, ValueError):
        return None

    return parsed.replace(tzinfo=_timezone()) if parsed.tzinfo is None else parsed


def _first_name(name: str | None) -> str:
    parts = (name or "").split()

    return parts[0].strip(",.") if parts else ""


def _greeting(name: str | None) -> str:
    first = _first_name(name)

    return f"Hola {first}," if first else "Hola,"


def _human_when(moment: datetime) -> str:
    local = moment.astimezone(_timezone())

    return f"{DAYS[local.weekday()]} {local.day} de {MONTHS[local.month - 1]} a las {local:%H:%M}"


def _token(email: str) -> str | None:
    secret = os.getenv("ADMIN_KEY")

    if not secret:
        return None

    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()[:32]


def valid_token(email: str, token: str) -> bool:
    expected = _token(email)

    return bool(expected) and hmac.compare_digest(expected, token or "")


def opt_out(email: str) -> None:
    connection = get_connection()
    connection.execute(
        "INSERT OR IGNORE INTO demo_email_optouts (email) VALUES (?)", (email.strip().lower(),)
    )
    connection.commit()
    connection.close()


def _opted_out(connection, email: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM demo_email_optouts WHERE email = ?", (email.strip().lower(),)
    ).fetchone() is not None


def _unsubscribe_line(email: str) -> str:
    base = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    token = _token(email)

    if base and token:
        return (
            "Si no quieres recibir más mensajes de seguimiento, puedes darte de baja aquí: "
            f"{base}/unsubscribe?e={quote(email)}&t={token}"
        )

    return "Si no quieres recibir más mensajes de seguimiento, responde a este correo con la palabra BAJA."


# --------------------------------------------------------------------- mensajes

def reminder_message(vertical: str, lead_name: str | None, scheduled: datetime) -> tuple[str, str]:
    business = business_name(vertical)
    when = _human_when(scheduled)

    subject = f"Recordatorio: tu cita en {business}, {when}"
    body = (
        f"{_greeting(lead_name)}\n\n"
        f"Te recordamos tu cita en {business}:\n\n"
        f"    {when}\n\n"
        "Si necesitas cambiarla o cancelarla, responde a este correo y lo gestionamos.\n"
        "¡Te esperamos!\n\n"
        f"{business}\n"
    )

    return subject, body


def followup_message(vertical: str, lead_name: str | None, email: str, step: int) -> tuple[str, str]:
    business = business_name(vertical)
    url = site_url_for(vertical)
    site = f" cuando quieras en {url}" if url else " cuando quieras"

    if step == 0:
        subject = f"¿Seguimos con tu consulta en {business}?"
        opening = f"Ayer estuviste hablando con el asistente de {business} y no llegamos a dejar tu cita agendada."
    else:
        subject = f"Una última nota de {business}"
        opening = (
            f"Hace unos días hablaste con el asistente de {business} y queríamos asegurarnos "
            "de que no te quedaste con dudas."
        )

    body = (
        f"{_greeting(lead_name)}\n\n"
        f"{opening}\n\n"
        f"Si sigues interesado/a, puedes retomarlo{site}, o responder a este correo y una persona te atiende.\n"
    )

    if step > 0:
        body += "\nNo te escribiremos más sobre este tema.\n"

    body += f"\nUn saludo,\n{business}\n\n--\n{_unsubscribe_line(email)}\n"

    return subject, body


# -------------------------------------------------------------------- candidatos

def _due_reminders(connection, now: datetime) -> list[dict]:
    hours = reminder_hours()
    allowed = sources()
    marks = ",".join("?" for _ in allowed)
    floor = (now.astimezone(_timezone()) - timedelta(days=1)).strftime("%Y-%m-%d")

    rows = connection.execute(
        f"""
        SELECT a.id, a.conversation_id, a.vertical, a.scheduled_at, a.lead_name,
               a.lead_email, a.created_at
        FROM demo_appointments a
        JOIN demo_conversations c ON c.id = a.conversation_id
        WHERE COALESCE(a.lead_email, '') != '' AND a.scheduled_at >= ?
          AND c.source IN ({marks})
        """,
        (floor, *allowed),
    ).fetchall()

    already = {
        (row["appointment_id"], row["kind"])
        for row in connection.execute("SELECT appointment_id, kind FROM demo_reminders_sent")
    }

    due = []

    for row in rows:
        if not is_valid_email(row["lead_email"]):
            continue

        scheduled = _parse_appointment(row["scheduled_at"])

        if scheduled is None or now >= scheduled - MIN_LEAD:
            continue

        booked_at = _parse_db_time(row["created_at"])

        for lead_hours in hours:  # de la ventana más cercana a la más lejana
            opens_at = scheduled - timedelta(hours=lead_hours)

            if now < opens_at or booked_at > opens_at:
                continue

            if (row["id"], f"h{lead_hours}") in already:
                continue

            due.append({
                "appointment_id": row["id"],
                "vertical": row["vertical"],
                "lead_name": row["lead_name"],
                "email": row["lead_email"],
                "scheduled": scheduled,
                "kind": f"h{lead_hours}",
                # Si se perdió una ventana más lejana, no se envía después.
                "claim_kinds": [f"h{other}" for other in hours if other >= lead_hours],
            })
            break

    return due


def _due_followups(connection, now: datetime, since: datetime) -> list[dict]:
    thresholds = followup_hours()
    allowed = sources()
    marks = ",".join("?" for _ in allowed)
    oldest = max(since, now - followup_max_age()).astimezone(UTC).strftime(DB_TIME)

    rows = connection.execute(
        f"""
        SELECT c.id, c.vertical, c.lead_data, c.updated_at, c.source
        FROM demo_conversations c
        WHERE c.source IN ({marks}) AND c.lead_status = 'nuevo' AND c.updated_at >= ?
          AND NOT EXISTS (SELECT 1 FROM demo_appointments a WHERE a.conversation_id = c.id)
          AND NOT EXISTS (
              SELECT 1 FROM demo_handoffs h
              WHERE h.conversation_id = c.id AND h.vertical = c.vertical AND h.source = c.source
          )
        """,
        (*allowed, oldest),
    ).fetchall()

    sent_rows = connection.execute(
        "SELECT conversation_id, step, sent_at FROM demo_followups_sent ORDER BY step"
    ).fetchall()
    sent: dict[int, list[datetime]] = {}

    for row in sent_rows:
        sent.setdefault(row["conversation_id"], []).append(_parse_db_time(row["sent_at"]))

    due = []

    for row in rows:
        try:
            lead = json.loads(row["lead_data"] or "{}")
        except ValueError:
            continue

        email = str(lead.get("email") or "").strip()

        if not is_valid_email(email) or _opted_out(connection, email):
            continue

        step = len(sent.get(row["id"], []))

        if step >= len(thresholds):
            continue

        if now - _parse_db_time(row["updated_at"]) < timedelta(hours=thresholds[step]):
            continue

        if step > 0:
            gap = timedelta(hours=thresholds[step] - thresholds[step - 1])

            if now - sent[row["id"]][-1] < gap:
                continue

        due.append({
            "conversation_id": row["id"],
            "vertical": row["vertical"],
            "lead_name": lead.get("name"),
            "email": email,
            "step": step,
        })

    return due


# ------------------------------------------------------------------- ejecución

def _claim(connection, table: str, key_column: str, key: int, kind_column: str, kinds: list, now: datetime) -> list | None:
    """
    Reserva el envío antes de hacerlo. Devuelve None si otro proceso (o una
    ejecución anterior) ya lo reservó; si no, devuelve lo que reservó ahora,
    para poder liberar exactamente eso si el envío falla.
    """

    sent_at = now.astimezone(UTC).strftime(DB_TIME)
    cursor = connection.execute(
        f"INSERT OR IGNORE INTO {table} ({key_column}, {kind_column}, sent_at) VALUES (?, ?, ?)",
        (key, kinds[0], sent_at),
    )

    if cursor.rowcount != 1:
        connection.commit()
        return None

    taken = [kinds[0]]

    for extra in kinds[1:]:
        cursor = connection.execute(
            f"INSERT OR IGNORE INTO {table} ({key_column}, {kind_column}, sent_at) VALUES (?, ?, ?)",
            (key, extra, sent_at),
        )

        if cursor.rowcount == 1:
            taken.append(extra)

    connection.commit()

    return taken


def _release(connection, table: str, key_column: str, key: int, kind_column: str, taken: list) -> None:
    for kind in taken:
        connection.execute(
            f"DELETE FROM {table} WHERE {key_column} = ? AND {kind_column} = ?", (key, kind)
        )

    connection.commit()


def run_once(now: datetime | None = None, dry_run: bool = False) -> dict:
    """
    Envía lo que toque en este momento. Con dry_run=True solo devuelve qué
    se enviaría, sin enviar nada ni guardar nada.
    """

    now = (now or datetime.now(UTC)).astimezone(UTC)
    summary = {"reminders": [], "followups": [], "skipped": None}

    if not dry_run and not smtp_configured():
        summary["skipped"] = "SMTP no configurado (SMTP_USER y SMTP_PASSWORD)."
        return summary

    connection = get_connection()

    try:
        since = _enabled_since(connection, now, persist=not dry_run)

        for item in _due_reminders(connection, now):
            entry = {"appointment_id": item["appointment_id"], "to": item["email"], "kind": item["kind"]}

            if dry_run:
                summary["reminders"].append(entry)
                continue

            taken = _claim(
                connection, "demo_reminders_sent", "appointment_id", item["appointment_id"], "kind", item["claim_kinds"], now
            )

            if taken is None:
                continue

            subject, body = reminder_message(item["vertical"], item["lead_name"], item["scheduled"])

            if send_email(subject, body, item["email"], reply_to_for(item["vertical"]), business_name(item["vertical"])):
                summary["reminders"].append(entry)
            else:
                _release(connection, "demo_reminders_sent", "appointment_id", item["appointment_id"], "kind", taken)

        for item in _due_followups(connection, now, since):
            entry = {"conversation_id": item["conversation_id"], "to": item["email"], "step": item["step"] + 1}

            if dry_run:
                summary["followups"].append(entry)
                continue

            taken = _claim(
                connection, "demo_followups_sent", "conversation_id", item["conversation_id"], "step", [item["step"]], now
            )

            if taken is None:
                continue

            subject, body = followup_message(item["vertical"], item["lead_name"], item["email"], item["step"])

            if send_email(subject, body, item["email"], reply_to_for(item["vertical"]), business_name(item["vertical"])):
                summary["followups"].append(entry)
            else:
                _release(connection, "demo_followups_sent", "conversation_id", item["conversation_id"], "step", taken)
    finally:
        connection.close()

    return summary


_started = False


def start_scheduler() -> bool:
    """Arranca el revisor en segundo plano (cada REMINDER_INTERVAL_MINUTES, 15 por defecto)."""

    global _started

    if _started or not enabled():
        return False

    _started = True
    minutes = os.getenv("REMINDER_INTERVAL_MINUTES", "15")
    interval = max(1, int(minutes) if minutes.isdigit() else 15) * 60

    def loop() -> None:
        time.sleep(30)  # deja arrancar la app antes del primer repaso

        while True:
            try:
                result = run_once()

                if result["reminders"] or result["followups"]:
                    logger.info(
                        "Recordatorios enviados: %d · seguimientos enviados: %d",
                        len(result["reminders"]), len(result["followups"]),
                    )
            except Exception:
                logger.exception("Fallo en el repaso de recordatorios y seguimiento")

            time.sleep(interval)

    threading.Thread(target=loop, daemon=True, name="reminders").start()
    logger.info("Recordatorios y seguimiento activados (cada %d min).", interval // 60)

    return True
