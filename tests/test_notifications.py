import email

from backend.services import notify


def test_widget_lead_notifies_the_verticals_own_address(chat, sent_notifications, monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL", "general@example.com")
    monkeypatch.setenv("NOTIFY_EMAIL_EXTRANJERIA", "acero@example.com")

    chat("extranjeria", source="widget").complete()

    assert len(sent_notifications) == 1
    notification = sent_notifications[0]
    assert notification["to"] == "acero@example.com"
    assert notification["subject"] == "Nuevo lead de Acero Pulido: Carlos Ruiz"
    assert "+34 600 123 456" in notification["body"]
    assert "carlos@example.com" in notification["body"]


def test_only_one_notification_per_completed_conversation(chat, sent_notifications, monkeypatch):
    monkeypatch.setattr(
        "backend.demo.orchestrator.generate_followup_reply",
        lambda prompt, message, conversation_history=None: "ok",
    )
    conversation = chat("extranjeria", source="widget")
    conversation.complete()
    conversation.send("gracias por todo")
    conversation.send("otra pregunta")

    assert len(sent_notifications) == 1


def test_demo_tests_do_not_notify_unless_enabled(chat, sent_notifications, monkeypatch):
    chat("extranjeria", source="demo").complete()
    assert sent_notifications == []

    monkeypatch.setenv("NOTIFY_DEMO_LEADS", "1")
    chat("extranjeria", source="demo").complete()
    assert len(sent_notifications) == 1


def test_urgent_lead_is_flagged_in_the_subject(chat, sent_notifications):
    chat("dental", source="widget").complete({"is_urgent": True})

    assert sent_notifications[0]["subject"].startswith("[URGENTE] ")
    assert "Prioridad: alta" in sent_notifications[0]["body"]


def test_incomplete_conversation_does_not_notify(chat, sent_notifications):
    conversation = chat("extranjeria", source="widget")
    conversation.send("hola")
    conversation.send("Carlos", field="name", value="Carlos")

    assert sent_notifications == []


def test_booking_notifies_and_warns_when_the_calendar_is_not_configured(chat, client, sent_notifications):
    conversation = chat("extranjeria", source="widget")
    conversation.complete()
    sent_notifications.clear()

    response = client.post(
        "/demo/book-appointment",
        json={"conversation_id": conversation.conversation_id, "scheduled_at": "2026-10-05T11:00:00"},
    )

    assert response.status_code == 200
    assert response.json()["calendar_status"] == "not_configured"
    assert len(sent_notifications) == 1
    assert "NO se añadió" in sent_notifications[0]["body"]


def test_business_lead_saves_and_notifies_the_owner(client, sent_notifications):
    response = client.post("/business-leads", json={
        "name": "Marta", "business_name": "Clínica Sol", "email": "marta@example.com",
        "vertical_interest": "Clínica dental", "message": "Quiero probarlo",
    })

    assert response.status_code == 200
    assert len(sent_notifications) == 1
    assert "Clínica Sol" in sent_notifications[0]["subject"]
    assert "marta@example.com" in sent_notifications[0]["body"]


def test_recipient_precedence(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    assert notify.notify_email_for() == "bot@example.com"

    monkeypatch.setenv("NOTIFY_EMAIL", "general@example.com")
    assert notify.notify_email_for() == "general@example.com"
    assert notify.notify_email_for("dental") == "general@example.com"

    monkeypatch.setenv("NOTIFY_EMAIL_DENTAL", "dentista@example.com")
    assert notify.notify_email_for("dental") == "dentista@example.com"
    assert notify.notify_email_for("hotel") == "general@example.com"


def test_send_notification_does_nothing_without_smtp_configured():
    assert notify.send_notification("Asunto", "Cuerpo", to="x@example.com") is False


def test_email_headers_cannot_be_injected_through_the_subject(monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(notify.smtplib, "SMTP", FakeSMTP)

    notify._send("Hola\nBcc: evil@example.com", "Cuerpo con acentos: teléfono", "dueño@example.com")

    message = sent[0]
    assert message["Bcc"] is None
    assert "\n" not in message["Subject"]
    assert email.message_from_string(message.as_string())["Subject"] is not None
    assert "teléfono" in message.get_content()


def test_smtp_failure_never_raises(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("sin red")

    monkeypatch.setenv("SMTP_USER", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(notify.smtplib, "SMTP", boom)

    notify._send("Asunto", "Cuerpo", "dueño@example.com")
