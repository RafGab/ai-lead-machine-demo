import re

import httpx
import pytest

from backend.services import calendar_service as calendar

CALENDAR_ID = "despacho@example.com"


@pytest.fixture
def google(monkeypatch):
    """
    Un Google Calendar de mentira. Como el real, rechaza con 400 las fechas
    de freeBusy que no llevan zona horaria. `google.busy` son los periodos
    ocupados que devuelve y `google.events` los eventos creados.
    """

    monkeypatch.setenv("GOOGLE_CALENDAR_ID_DESPACHO", CALENDAR_ID)
    monkeypatch.delenv("GOOGLE_CALENDAR_TIMEZONE", raising=False)
    monkeypatch.setattr(calendar, "_get_access_token", lambda: "token")
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_START", 10)
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_END", 19)
    monkeypatch.setattr(calendar, "BUSINESS_DAYS", {0, 1, 2, 3, 4})

    class FakeGoogle:
        busy = []
        events = []

    fake = FakeGoogle()

    def fake_post(url, headers=None, json=None, timeout=None, params=None, **kwargs):
        request = httpx.Request("POST", url)

        if url.endswith("/freeBusy"):
            if not re.search(r"(Z|[+-]\d\d:\d\d)$", json["timeMin"]):
                return httpx.Response(400, request=request, text='{"error":{"message":"Bad Request"}}')

            body = {"calendars": {CALENDAR_ID: {"busy": fake.busy}}}
            return httpx.Response(200, request=request, json=body)

        fake.events.append(json)
        return httpx.Response(200, request=request, json={"id": f"evento-{len(fake.events)}"})

    monkeypatch.setattr(calendar.httpx, "post", fake_post)

    return fake


def book(client, conversation_id, scheduled_at):
    return client.post(
        "/demo/book-appointment",
        json={"conversation_id": conversation_id, "scheduled_at": scheduled_at},
    )


def new_conversation(chat):
    conversation = chat("despacho")
    conversation.send("hola")

    return conversation.conversation_id


def test_booking_a_free_slot_creates_the_calendar_event(client, chat, google, sent_notifications):
    response = book(client, new_conversation(chat), "2026-10-15T10:00:00")

    assert response.status_code == 200
    data = response.json()
    assert data["calendar_status"] == "synced"
    assert data["calendar_event_id"] == "evento-1"
    assert len(google.events) == 1


def test_booking_a_busy_slot_offers_alternatives_instead_of_failing(client, chat, google, sent_notifications):
    google.busy = [{"start": "2026-10-15T08:00:00Z", "end": "2026-10-15T08:30:00Z"}]  # 10:00 Madrid

    response = book(client, new_conversation(chat), "2026-10-15T10:00:00")

    assert response.status_code == 200
    data = response.json()
    assert data["calendar_status"] == "unavailable"
    assert data["alternative_slots"][0] == "2026-10-15T10:30:00"
    assert google.events == []
