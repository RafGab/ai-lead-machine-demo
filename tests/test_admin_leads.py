import csv
import io
import itertools

import pytest

from backend.demo import leads_service

KEY = "clave-de-prueba"
_counter = itertools.count(1)


@pytest.fixture(autouse=True)
def admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", KEY)


def unique_name():
    """La base de datos de tests se comparte: cada test busca a su propio lead."""

    return f"Lead Prueba {next(_counter)}"


def fetch(client, **params):
    response = client.get("/admin/leads", params={"key": KEY, **params})
    assert response.status_code == 200, response.text

    return response.json()


def find(payload, name):
    return next((lead for lead in payload["leads"] if lead["name"] == name), None)


def completed_lead(chat, name, source="widget", vertical="extranjeria", **overrides):
    conversation = chat(vertical, source=source)
    conversation.complete({"name": name, **overrides})

    return conversation


def test_admin_key_is_required(client):
    assert client.get("/admin/leads").status_code == 403
    assert client.get("/admin/leads", params={"key": "otra"}).status_code == 403
    assert client.get("/admin/leads.csv").status_code == 403
    assert client.post("/admin/leads/c-1/status", json={"status": "cerrado"}).status_code == 403


def test_completed_lead_from_the_site_shows_contact_and_details(client, chat):
    name = unique_name()
    completed_lead(chat, name)

    lead = find(fetch(client), name)

    assert lead["vertical"] == "extranjeria"
    assert lead["vertical_label"] == "Acero Pulido"
    assert lead["source"] == "widget"
    assert lead["status"] == "nuevo"
    assert lead["completed"] is True
    assert lead["phone"] == "+34 600 123 456"
    assert lead["email"] == "carlos@example.com"
    assert {"label": "nacionalidad", "value": "peruana"} in lead["details"]
    assert lead["created_at"].endswith("Z")


def test_demo_tests_are_hidden_unless_all_sources_are_requested(client, chat):
    name = unique_name()
    completed_lead(chat, name, source="demo")

    assert find(fetch(client), name) is None
    assert find(fetch(client, scope="all"), name)["source"] == "demo"


def test_conversations_without_a_way_to_contact_are_hidden_by_default(client, chat):
    name = unique_name()
    conversation = chat("extranjeria", source="widget")
    conversation.send("hola")
    conversation.send(name, field="name", value=name)

    assert find(fetch(client), name) is None
    assert find(fetch(client, incomplete="true"), name)["phone"] == ""


def test_vertical_filter(client, chat):
    dental_name, extranjeria_name = unique_name(), unique_name()
    completed_lead(chat, dental_name, vertical="dental")
    completed_lead(chat, extranjeria_name)

    dental = fetch(client, vertical="dental")

    assert find(dental, dental_name) is not None
    assert find(dental, extranjeria_name) is None


def test_status_and_note_can_be_updated_and_filtered(client, chat):
    name = unique_name()
    completed_lead(chat, name)
    lead = find(fetch(client), name)

    response = client.post(
        f"/admin/leads/{lead['id']}/status",
        params={"key": KEY},
        json={"status": "contactado", "note": "Llamado el lunes, pide más información"},
    )

    assert response.status_code == 200
    updated = find(fetch(client), name)
    assert updated["status"] == "contactado"
    assert updated["note"] == "Llamado el lunes, pide más información"
    assert find(fetch(client, status="contactado"), name) is not None
    assert find(fetch(client, status="nuevo"), name) is None

    client.post(f"/admin/leads/{lead['id']}/status", params={"key": KEY}, json={"status": "cerrado"})
    closed = find(fetch(client), name)
    assert closed["status"] == "cerrado"
    assert closed["note"] == "Llamado el lunes, pide más información", "Sin nota nueva se conserva la anterior."


def test_counts_reflect_each_status(client, chat):
    before = fetch(client)["counts"]
    name = unique_name()
    completed_lead(chat, name)

    after = fetch(client)["counts"]
    assert after["nuevo"] == before["nuevo"] + 1
    assert after["total"] == before["total"] + 1


def test_invalid_status_and_unknown_or_malformed_ids_are_rejected(client):
    assert client.post("/admin/leads/c-1/status", params={"key": KEY}, json={"status": "hecho"}).status_code == 400
    assert client.post("/admin/leads/x-1/status", params={"key": KEY}, json={"status": "cerrado"}).status_code == 400
    assert client.post("/admin/leads/c-abc/status", params={"key": KEY}, json={"status": "cerrado"}).status_code == 400
    assert client.post("/admin/leads/c-999999/status", params={"key": KEY}, json={"status": "cerrado"}).status_code == 404
    assert client.get("/admin/leads", params={"key": KEY, "status": "hecho"}).status_code == 400
    assert client.post(
        "/admin/leads/c-1/status", params={"key": KEY}, json={"status": "cerrado", "note": "a" * 501}
    ).status_code == 422


def test_handoff_marks_the_lead_urgent_and_sorts_it_first(client, chat):
    plain_name, urgent_name = unique_name(), unique_name()
    completed_lead(chat, plain_name)
    urgent = completed_lead(chat, urgent_name)
    client.post("/demo/handoff", json={
        "vertical": "extranjeria", "source": "widget", "conversation_id": urgent.conversation_id,
        "contact": "+34 655 000 111", "note": "Tengo prisa",
    })

    leads = fetch(client)["leads"]
    names = [lead["name"] for lead in leads]

    assert find({"leads": leads}, urgent_name)["urgent"] is True
    assert find({"leads": leads}, urgent_name)["handoff_note"] == "Tengo prisa"
    assert find({"leads": leads}, plain_name)["urgent"] is False
    assert names.index(urgent_name) < names.index(plain_name)


def test_handoff_contact_makes_an_incomplete_conversation_contactable(client, chat):
    name = unique_name()
    conversation = chat("extranjeria", source="widget")
    conversation.send("hola")
    conversation.send(name, field="name", value=name)
    client.post("/demo/handoff", json={
        "vertical": "extranjeria", "source": "widget", "conversation_id": conversation.conversation_id,
        "contact": "ana.handoff@example.com",
    })

    lead = find(fetch(client), name)

    assert lead["email"] == "ana.handoff@example.com"
    assert lead["urgent"] is True
    assert lead["kind"] == "conversation"


def test_handoff_without_a_conversation_is_its_own_lead(client):
    name = unique_name()
    client.post("/demo/handoff", json={
        "vertical": "hotel", "source": "widget", "contact": "+34 655 777 888", "name": name,
    })

    lead = find(fetch(client), name)

    assert lead["kind"] == "handoff"
    assert lead["id"].startswith("h-")
    assert lead["phone"] == "+34 655 777 888"
    assert lead["urgent"] is True

    client.post(f"/admin/leads/{lead['id']}/status", params={"key": KEY}, json={"status": "contactado"})
    assert find(fetch(client), name)["status"] == "contactado"


def test_appointment_is_attached_to_the_lead(client, chat):
    name = unique_name()
    conversation = completed_lead(chat, name)
    client.post("/demo/book-appointment", json={
        "conversation_id": conversation.conversation_id, "scheduled_at": "2026-10-05T11:00:00",
    })

    lead = find(fetch(client), name)

    assert lead["appointment"]["scheduled_at"] == "2026-10-05T11:00:00"


def test_csv_export_opens_cleanly_in_excel_and_neutralises_formulas(client, chat):
    name = "=HYPERLINK(\"http://malo.example\",\"clic\")"
    completed_lead(chat, name)

    response = client.get("/admin/leads.csv", params={"key": KEY})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith("﻿".encode("utf-8")), "BOM para que Excel lea los acentos"

    rows = list(csv.reader(io.StringIO(response.text.lstrip("﻿"))))
    assert rows[0][:6] == ["Fecha (UTC)", "Rubro", "Origen", "Estado", "Urgente", "Nombre"]

    row = next(r for r in rows[1:] if "HYPERLINK" in r[5])
    assert row[5].startswith("'="), "Un texto que empieza por = no debe ejecutarse como fórmula"
    assert row[6] == "+34 600 123 456", "Los teléfonos con + se respetan"
    assert row[2] == "Web del cliente"


@pytest.mark.parametrize("value,expected", [
    ("=1+1", "'=1+1"), ("@SUM(A1)", "'@SUM(A1)"), ("+34 600 123 456", "+34 600 123 456"),
    ("-5 días", "'-5 días"), ("Ana", "Ana"), ("", ""),
])
def test_csv_safe(value, expected):
    assert leads_service._csv_safe(value) == expected
