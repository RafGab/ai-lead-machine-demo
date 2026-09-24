import itertools

import pytest

_counter = itertools.count(1000000)


def unique_phone():
    """La base de datos de tests se comparte: cada test usa un teléfono distinto."""

    return f"+34 6{next(_counter)}"


def post_handoff(client, **overrides):
    body = {"vertical": "extranjeria", "source": "widget", "contact": unique_phone(), "name": "Ana"}
    body.update(overrides)

    return client.post("/demo/handoff", json=body)


def test_handoff_from_a_real_site_notifies_the_team_urgently(client, chat, sent_notifications, monkeypatch):
    monkeypatch.setenv("NOTIFY_EMAIL_EXTRANJERIA", "acero@example.com")
    conversation = chat("extranjeria", source="widget")
    conversation.send("hola")
    conversation.send("Ana", field="name", value="Ana")
    phone = unique_phone()

    response = post_handoff(client, conversation_id=conversation.conversation_id, contact=phone, note="Es urgente")

    assert response.status_code == 200
    assert response.json()["message"].startswith("¡Listo! Avisé al equipo")
    assert len(sent_notifications) == 1
    notification = sent_notifications[0]
    assert notification["to"] == "acero@example.com"
    assert notification["subject"] == "[URGENTE] Ana quiere hablar con una persona (Acero Pulido)"
    assert phone in notification["body"]
    assert "Es urgente" in notification["body"]
    assert "Cliente: Ana" in notification["body"]


def test_email_is_accepted_as_contact(client, sent_notifications):
    response = post_handoff(client, contact="ana@example.com")

    assert response.status_code == 200
    assert "ana@example.com" in sent_notifications[0]["body"]


@pytest.mark.parametrize("contact", ["abc", "123", "hola@", "abc123456789", "no tengo"])
def test_invalid_contact_is_rejected_with_a_helpful_message(client, sent_notifications, contact):
    response = post_handoff(client, contact=contact)

    assert response.status_code == 400
    assert "teléfono válido" in response.json()["detail"]
    assert sent_notifications == []


def test_contact_already_given_in_the_conversation_is_reused(client, chat, sent_notifications):
    conversation = chat("extranjeria", source="widget")
    conversation.complete()
    sent_notifications.clear()

    response = post_handoff(client, conversation_id=conversation.conversation_id, contact="", name="")

    assert response.status_code == 200
    assert len(sent_notifications) == 1
    assert "+34 600 123 456" in sent_notifications[0]["body"]
    assert "Carlos Ruiz" in sent_notifications[0]["subject"]


def test_missing_contact_and_no_conversation_asks_for_one(client):
    response = post_handoff(client, contact="")

    assert response.status_code == 400


def test_demo_requests_do_not_email_and_say_so(client, sent_notifications):
    response = post_handoff(client, source="demo")

    assert response.status_code == 200
    assert "En una web real" in response.json()["message"]
    assert sent_notifications == []


def test_double_click_does_not_send_the_email_twice(client, sent_notifications):
    phone = unique_phone()

    first = post_handoff(client, contact=phone)
    second = post_handoff(client, contact=phone)

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True
    assert second.json()["message"] == first.json()["message"]
    assert len(sent_notifications) == 1


def test_works_for_inmobiliaria_conversations(client, chat, sent_notifications):
    conversation = chat("inmobiliaria", source="widget")
    conversation.send("hola")
    conversation.send("compra", field="operation", value="compra")

    response = post_handoff(client, vertical="inmobiliaria", conversation_id=conversation.conversation_id)

    assert response.status_code == 200
    assert "(Inmobiliaria)" in sent_notifications[0]["subject"]
    assert "operación: compra" in sent_notifications[0]["body"]


def test_unknown_vertical_and_conversation_are_rejected(client):
    assert post_handoff(client, vertical="no-existe").status_code == 400
    assert post_handoff(client, conversation_id=999999).status_code == 400


def test_overlong_note_is_rejected(client):
    assert post_handoff(client, note="a" * 501).status_code == 422


def test_handoffs_show_up_in_the_insights_panel(client, monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "clave-de-prueba")
    before = client.get("/admin/insights-demo?vertical=gimnasio&key=clave-de-prueba").json()

    post_handoff(client, vertical="gimnasio")
    post_handoff(client, vertical="gimnasio", source="demo")
    after = client.get("/admin/insights-demo?vertical=gimnasio&key=clave-de-prueba").json()

    assert after["handoffs_from_site"] == before["handoffs_from_site"] + 1
    assert any("han pedido hablar con una persona" in line for line in after["narrative"])
