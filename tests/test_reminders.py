import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from backend.database.database import get_connection
from backend.demo import reminders

UTC = timezone.utc
MADRID = ZoneInfo("Europe/Madrid")
T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)  # "ahora" de las pruebas


def _db(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _local_iso(moment: datetime) -> str:
    return moment.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M")


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    """Base de datos limpia para cada prueba y SMTP "configurado"."""

    connection = get_connection()
    for table in (
        "demo_appointments", "demo_handoffs", "demo_messages", "demo_conversations",
        "demo_reminders_sent", "demo_followups_sent", "demo_email_optouts", "demo_reminder_settings",
    ):
        connection.execute(f"DELETE FROM {table}")
    connection.commit()
    connection.close()

    monkeypatch.setenv("SMTP_USER", "avisos@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "x")
    monkeypatch.setenv("ADMIN_KEY", "clave-admin")
    monkeypatch.setenv("COMERCIAL_EMAIL_EXTRANJERIA", "acero@example.com")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("REMINDER_HOURS_BEFORE", raising=False)
    monkeypatch.delenv("FOLLOWUP_AFTER_HOURS", raising=False)
    monkeypatch.delenv("REMINDERS_SOURCES", raising=False)


class Outbox(list):
    """Lista de correos "enviados" con un interruptor para simular fallos de SMTP."""

    def __init__(self):
        super().__init__()
        self.state = {"ok": True}


@pytest.fixture
def mail(monkeypatch):
    sent = Outbox()

    def fake(subject, body, to, reply_to=None, from_name=None):
        if not sent.state["ok"]:
            return False
        sent.append({"subject": subject, "body": body, "to": to, "reply_to": reply_to, "from_name": from_name})
        return True

    monkeypatch.setattr(reminders, "send_email", fake)
    return sent


def _since(moment: datetime = T0 - timedelta(days=30)):
    connection = get_connection()
    connection.execute(
        "INSERT OR REPLACE INTO demo_reminder_settings (key, value) VALUES ('enabled_since', ?)", (_db(moment),)
    )
    connection.commit()
    connection.close()


def _conversation(
    *, email="ana@example.com", name="Ana Pérez", source="widget", updated=None,
    lead_status="nuevo", vertical="extranjeria",
) -> int:
    lead = {"name": name, "phone": "+34 600 000 000"}
    if email:
        lead["email"] = email

    updated = updated or T0 - timedelta(hours=2)
    connection = get_connection()
    cursor = connection.execute(
        "INSERT INTO demo_conversations (vertical, lead_data, source, lead_status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (vertical, json.dumps(lead), source, lead_status, _db(updated), _db(updated)),
    )
    connection.commit()
    connection.close()
    return cursor.lastrowid


def _appointment(conversation_id, *, scheduled, booked, email="ana@example.com", name="Ana Pérez", vertical="extranjeria"):
    connection = get_connection()
    cursor = connection.execute(
        "INSERT INTO demo_appointments (conversation_id, vertical, scheduled_at, lead_name, lead_email, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (conversation_id, vertical, _local_iso(scheduled), name, email, _db(booked)),
    )
    connection.commit()
    connection.close()
    return cursor.lastrowid


# ----------------------------------------------------------------- recordatorios

def test_sends_a_reminder_the_day_before_and_only_once(mail):
    conversation = _conversation()
    _appointment(conversation, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))

    result = reminders.run_once(now=T0)
    assert len(result["reminders"]) == 1
    assert len(mail) == 1

    message = mail[0]
    assert message["to"] == "ana@example.com"
    assert message["reply_to"] == "acero@example.com"
    assert message["from_name"] == "Acero Pulido"
    assert message["subject"].startswith("Recordatorio: tu cita en Acero Pulido")
    assert "Hola Ana," in message["body"]
    assert "viernes 2 de octubre a las 13:00" in message["body"]  # 11:00 UTC = 13:00 en Madrid

    reminders.run_once(now=T0 + timedelta(minutes=15))
    assert len(mail) == 1


def test_no_reminder_when_the_booking_was_made_inside_the_window(mail):
    conversation = _conversation()
    _appointment(conversation, scheduled=T0 + timedelta(hours=20), booked=T0 - timedelta(hours=1))

    reminders.run_once(now=T0)

    assert mail == []


def test_no_reminder_too_early_or_too_close_or_for_past_appointments(mail):
    conversation = _conversation()
    _appointment(conversation, scheduled=T0 + timedelta(hours=40), booked=T0 - timedelta(days=3))
    _appointment(conversation, scheduled=T0 + timedelta(minutes=10), booked=T0 - timedelta(days=3))
    _appointment(conversation, scheduled=T0 - timedelta(hours=3), booked=T0 - timedelta(days=3))

    reminders.run_once(now=T0)

    assert mail == []


def test_no_reminder_without_a_valid_email_or_from_the_demo(mail):
    widget = _conversation(email=None)
    _appointment(widget, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2), email=None)
    _appointment(widget, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2), email="no-es-un-correo")
    demo = _conversation(source="demo")
    _appointment(demo, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))

    reminders.run_once(now=T0)

    assert mail == []


def test_second_reminder_window_and_skipped_windows(mail, monkeypatch):
    monkeypatch.setenv("REMINDER_HOURS_BEFORE", "24,2")
    conversation = _conversation()
    early = _appointment(conversation, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))
    # Esta cita se hizo hace 3 días pero el revisor estuvo parado: ya solo queda 1,5 h.
    late = _appointment(conversation, scheduled=T0 + timedelta(hours=1, minutes=40), booked=T0 - timedelta(days=3))

    reminders.run_once(now=T0)
    assert len(mail) == 2  # h24 de la primera y h2 de la segunda

    reminders.run_once(now=T0 + timedelta(minutes=15))
    assert len(mail) == 2  # la ventana de 24 h de la segunda no se envía después de la de 2 h

    # 22 h después entra la ventana de 2 h de la primera.
    reminders.run_once(now=T0 + timedelta(hours=21, minutes=30))
    assert len(mail) == 3

    connection = get_connection()
    kinds = {(r["appointment_id"], r["kind"]) for r in connection.execute("SELECT * FROM demo_reminders_sent")}
    connection.close()
    assert (early, "h24") in kinds and (early, "h2") in kinds and (late, "h2") in kinds and (late, "h24") in kinds


def test_a_failed_send_is_retried_and_never_unmarks_earlier_sends(mail, monkeypatch):
    monkeypatch.setenv("REMINDER_HOURS_BEFORE", "24,2")
    conversation = _conversation()
    appointment = _appointment(conversation, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))

    reminders.run_once(now=T0)
    assert len(mail) == 1  # h24

    mail.state["ok"] = False
    reminders.run_once(now=T0 + timedelta(hours=21, minutes=30))  # h2 falla
    assert len(mail) == 1

    mail.state["ok"] = True
    reminders.run_once(now=T0 + timedelta(hours=21, minutes=45))  # se reintenta h2
    assert len(mail) == 2

    reminders.run_once(now=T0 + timedelta(hours=21, minutes=50))
    assert len(mail) == 2

    connection = get_connection()
    kinds = {r["kind"] for r in connection.execute("SELECT kind FROM demo_reminders_sent WHERE appointment_id = ?", (appointment,))}
    connection.close()
    assert kinds == {"h24", "h2"}


# -------------------------------------------------------------------- seguimiento

def test_followup_steps_are_spaced_and_limited_to_two(mail):
    _since()
    conversation = _conversation(updated=T0 - timedelta(hours=25))

    reminders.run_once(now=T0)
    assert len(mail) == 1
    assert mail[0]["subject"] == "¿Seguimos con tu consulta en Acero Pulido?"
    assert "Ayer estuviste hablando" in mail[0]["body"]
    assert "responde a este correo con la palabra BAJA" in mail[0]["body"]

    reminders.run_once(now=T0 + timedelta(hours=20))
    assert len(mail) == 1  # todavía no pasó el margen entre mensajes

    reminders.run_once(now=T0 + timedelta(hours=49))
    assert len(mail) == 2
    assert mail[1]["subject"] == "Una última nota de Acero Pulido"
    assert "No te escribiremos más" in mail[1]["body"]

    reminders.run_once(now=T0 + timedelta(days=4))
    assert len(mail) == 2

    connection = get_connection()
    steps = [r["step"] for r in connection.execute("SELECT step FROM demo_followups_sent WHERE conversation_id = ?", (conversation,))]
    connection.close()
    assert sorted(steps) == [0, 1]


def test_no_followup_before_the_wait_or_after_the_max_age(mail):
    _since()
    _conversation(updated=T0 - timedelta(hours=5))
    _conversation(updated=T0 - timedelta(days=9), email="vieja@example.com")

    reminders.run_once(now=T0)

    assert mail == []


@pytest.mark.parametrize("case", ["appointment", "handoff", "contacted", "closed", "no_email", "demo", "opted_out"])
def test_no_followup_when_the_lead_is_already_handled(mail, case):
    _since()
    status = {"contacted": "contactado", "closed": "cerrado"}.get(case, "nuevo")
    conversation = _conversation(
        updated=T0 - timedelta(hours=30),
        email=None if case == "no_email" else "ana@example.com",
        source="demo" if case == "demo" else "widget",
        lead_status=status,
    )

    connection = get_connection()
    if case == "handoff":
        connection.execute(
            "INSERT INTO demo_handoffs (vertical, source, conversation_id, contact, contact_type) "
            "VALUES ('extranjeria', 'widget', ?, 'ana@example.com', 'email')", (conversation,),
        )
    connection.commit()
    connection.close()

    if case == "appointment":
        _appointment(conversation, scheduled=T0 + timedelta(days=5), booked=T0 - timedelta(hours=29))
    if case == "opted_out":
        reminders.opt_out("ANA@example.com")

    reminders.run_once(now=T0)

    assert mail == []


def test_no_followup_burst_for_leads_from_before_activation(mail):
    # Primera ejecución en T0: se fija "desde cuándo está activo".
    reminders.run_once(now=T0)
    _conversation(updated=T0 - timedelta(hours=30))  # anterior a la activación

    reminders.run_once(now=T0 + timedelta(minutes=15))

    assert mail == []


def test_dry_run_reports_without_sending_or_recording(mail):
    _since()
    _conversation(updated=T0 - timedelta(hours=26), email="pendiente@example.com")
    booked = _conversation(updated=T0 - timedelta(hours=2))
    _appointment(booked, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))

    result = reminders.run_once(now=T0, dry_run=True)

    assert len(result["reminders"]) == 1 and len(result["followups"]) == 1
    assert mail == []

    connection = get_connection()
    assert connection.execute("SELECT COUNT(*) AS n FROM demo_reminders_sent").fetchone()["n"] == 0
    assert connection.execute("SELECT COUNT(*) AS n FROM demo_followups_sent").fetchone()["n"] == 0
    connection.close()


def test_skips_everything_without_smtp(mail, monkeypatch):
    monkeypatch.delenv("SMTP_USER")
    conversation = _conversation()
    _appointment(conversation, scheduled=T0 + timedelta(hours=23), booked=T0 - timedelta(days=2))

    result = reminders.run_once(now=T0)

    assert "SMTP" in result["skipped"]
    assert mail == []


# ---------------------------------------------- baja, rutas de administración, arranque

def test_followup_email_has_a_signed_unsubscribe_link_that_works(mail, client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://backend.example.com/")
    monkeypatch.setenv("SITE_URL", "https://go2spain-site.onrender.com")
    _since()
    _conversation(updated=T0 - timedelta(hours=26))

    reminders.run_once(now=T0)

    body = mail[0]["body"]
    assert "https://go2spain-site.onrender.com" in body
    link = next(line for line in body.splitlines() if "/unsubscribe?" in line).split("aquí: ")[1]
    assert link.startswith("https://backend.example.com/unsubscribe?e=ana%40example.com&t=")

    path = link.replace("https://backend.example.com", "")
    assert client.get(path).status_code == 200

    _conversation(updated=T0 - timedelta(hours=26), email="ana@example.com")
    reminders.run_once(now=T0 + timedelta(minutes=30))
    assert len(mail) == 1  # ya se dio de baja: la segunda conversación no recibe nada


def test_unsubscribe_rejects_a_forged_token(client):
    response = client.get("/unsubscribe?e=ana%40example.com&t=falso")

    assert response.status_code == 400

    connection = get_connection()
    assert connection.execute("SELECT COUNT(*) AS n FROM demo_email_optouts").fetchone()["n"] == 0
    connection.close()


def test_admin_routes_need_the_key_and_run_needs_reminders_enabled(client, mail, monkeypatch):
    assert client.post("/admin/reminders/run").status_code == 403
    assert client.post("/admin/reminders/run?key=mala").status_code == 403
    assert client.post("/admin/reminders/optout?key=mala", json={"email": "a@b.co"}).status_code == 403

    dry = client.post("/admin/reminders/run?key=clave-admin")
    assert dry.status_code == 200 and dry.json()["reminders"] == []

    monkeypatch.delenv("REMINDERS_ENABLED", raising=False)
    assert client.post("/admin/reminders/run?key=clave-admin&dry_run=false").status_code == 409

    monkeypatch.setenv("REMINDERS_ENABLED", "1")
    assert client.post("/admin/reminders/run?key=clave-admin&dry_run=false").status_code == 200

    assert client.post("/admin/reminders/optout?key=clave-admin", json={"email": "Baja@Example.com"}).status_code == 200
    connection = get_connection()
    assert connection.execute("SELECT email FROM demo_email_optouts").fetchone()["email"] == "baja@example.com"
    connection.close()


def test_scheduler_is_off_unless_enabled(monkeypatch):
    monkeypatch.setattr(reminders, "_started", False)
    monkeypatch.delenv("REMINDERS_ENABLED", raising=False)

    assert reminders.start_scheduler() is False
    assert reminders._started is False
