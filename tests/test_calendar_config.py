from datetime import datetime

import pytest

from backend.services import calendar_service as calendar


def test_calendar_id_prefers_the_verticals_own_calendar(monkeypatch):
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "general")
    monkeypatch.setenv("GOOGLE_CALENDAR_ID_EXTRANJERIA", "acero")

    assert calendar._calendar_id_for("extranjeria") == "acero"
    assert calendar._calendar_id_for("dental") == "general"
    assert calendar._calendar_id_for(None) == "general"


def test_comercial_email_falls_back_to_the_generic_one(monkeypatch):
    monkeypatch.setenv("COMERCIAL_EMAIL", "ventas@example.com")
    monkeypatch.setenv("COMERCIAL_EMAIL_EXTRANJERIA", "asesor@example.com")

    assert calendar._comercial_email_for("extranjeria") == "asesor@example.com"
    assert calendar._comercial_email_for("hotel") == "ventas@example.com"


def test_business_hours_per_vertical_with_generic_fallback(monkeypatch):
    monkeypatch.setenv("BUSINESS_HOURS_START_EXTRANJERIA", "9")
    monkeypatch.setenv("BUSINESS_HOURS_END_EXTRANJERIA", "14")
    monkeypatch.setenv("BUSINESS_DAYS_EXTRANJERIA", "0,1,2")

    assert calendar._business_hours_for("extranjeria") == (9, 14, {0, 1, 2})

    start, end, days = calendar._business_hours_for("hotel")
    assert (start, end, days) == (
        calendar.BUSINESS_HOURS_START, calendar.BUSINESS_HOURS_END, calendar.BUSINESS_DAYS
    )


@pytest.mark.parametrize("moment,expected", [
    (datetime(2026, 10, 5, 10, 0), True),    # lunes 10:00
    (datetime(2026, 10, 5, 19, 0), False),   # lunes, ya cerrado
    (datetime(2026, 10, 3, 11, 0), False),   # sábado
])
def test_within_business_hours_with_default_schedule(monkeypatch, moment, expected):
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_START", 10)
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_END", 19)
    monkeypatch.setattr(calendar, "BUSINESS_DAYS", {0, 1, 2, 3, 4})

    assert calendar._within_business_hours(moment) is expected


def test_missing_calendar_raises_a_clear_error_naming_the_vertical():
    with pytest.raises(calendar.CalendarNotConfigured) as error:
        calendar.create_event("Cita", "desc", "2026-10-05T11:00:00", vertical="extranjeria")

    assert "GOOGLE_CALENDAR_ID_EXTRANJERIA" in str(error.value)


def test_scopes_allow_checking_availability_and_creating_events():
    from backend.services import calendar_service

    assert "https://www.googleapis.com/auth/calendar.events" in calendar_service.SCOPES
    assert "https://www.googleapis.com/auth/calendar.freebusy" in calendar_service.SCOPES


def test_google_error_body_is_logged(caplog):
    import httpx
    import pytest

    from backend.services import calendar_service

    request = httpx.Request("POST", "https://www.googleapis.com/calendar/v3/freeBusy")
    response = httpx.Response(403, request=request, text='{"error":{"message":"Insufficient Permission"}}')

    with caplog.at_level("ERROR"), pytest.raises(httpx.HTTPStatusError):
        calendar_service._raise_for_google_error(response)

    assert "Insufficient Permission" in caplog.text


def _fake_freebusy(monkeypatch, busy, sent):
    """Sustituye la llamada a Google: guarda lo enviado y devuelve `busy`."""
    import httpx

    monkeypatch.setenv("GOOGLE_CALENDAR_ID_DESPACHO", "despacho@example.com")
    monkeypatch.delenv("GOOGLE_CALENDAR_TIMEZONE", raising=False)
    monkeypatch.delenv("BUSINESS_HOURS_START_DESPACHO", raising=False)
    monkeypatch.delenv("BUSINESS_HOURS_END_DESPACHO", raising=False)
    monkeypatch.delenv("BUSINESS_DAYS_DESPACHO", raising=False)
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_START", 10)
    monkeypatch.setattr(calendar, "BUSINESS_HOURS_END", 19)
    monkeypatch.setattr(calendar, "BUSINESS_DAYS", {0, 1, 2, 3, 4})
    monkeypatch.setattr(calendar, "_get_access_token", lambda: "token")

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        sent.update(json)
        request = httpx.Request("POST", url)
        body = {"calendars": {"despacho@example.com": {"busy": busy}}}
        return httpx.Response(200, request=request, json=body)

    monkeypatch.setattr(calendar.httpx, "post", fake_post)


def test_freebusy_request_carries_the_calendars_time_zone(monkeypatch):
    # Regresión: la cita llega como "2026-10-15T10:00:00" (sin zona) y Google
    # respondía 400 Bad Request porque freeBusy exige zona horaria.
    sent = {}
    _fake_freebusy(monkeypatch, [], sent)

    assert calendar.is_slot_available("2026-10-15T10:00:00", vertical="despacho") is True

    assert sent["timeMin"] == "2026-10-15T10:00:00+02:00"
    assert sent["timeMax"] == "2026-10-15T10:30:00+02:00"
    assert sent["timeZone"] == "Europe/Madrid"


def test_freebusy_uses_winter_offset_after_the_clock_change(monkeypatch):
    sent = {}
    _fake_freebusy(monkeypatch, [], sent)

    calendar.is_slot_available("2026-11-12T10:00:00", vertical="despacho")

    assert sent["timeMin"] == "2026-11-12T10:00:00+01:00"


def test_freebusy_respects_the_configured_time_zone(monkeypatch):
    sent = {}
    _fake_freebusy(monkeypatch, [], sent)
    monkeypatch.setenv("GOOGLE_CALENDAR_TIMEZONE", "America/Bogota")

    calendar.is_slot_available("2026-10-15T10:00:00", vertical="despacho")

    assert sent["timeMin"] == "2026-10-15T10:00:00-05:00"


@pytest.mark.parametrize("busy_start,busy_end", [
    ("2026-10-15T10:00:00+02:00", "2026-10-15T10:30:00+02:00"),  # en la zona del calendario
    ("2026-10-15T08:00:00Z", "2026-10-15T08:30:00Z"),            # misma hora en UTC
])
def test_busy_slot_is_reported_unavailable_without_mixing_naive_and_aware(
    monkeypatch, busy_start, busy_end
):
    sent = {}
    _fake_freebusy(monkeypatch, [{"start": busy_start, "end": busy_end}], sent)

    assert calendar.is_slot_available("2026-10-15T10:00:00", vertical="despacho") is False
    assert calendar.is_slot_available("2026-10-15T11:00:00", vertical="despacho") is True


def test_alternative_slots_skip_busy_periods_and_stay_in_local_time(monkeypatch):
    sent = {}
    busy = [{"start": "2026-10-15T08:00:00Z", "end": "2026-10-15T09:00:00Z"}]  # 10:00-11:00 Madrid
    _fake_freebusy(monkeypatch, busy, sent)

    slots = calendar.suggest_alternative_slots(
        "2026-10-15T10:00:00", count=3, vertical="despacho"
    )

    assert slots == [
        "2026-10-15T11:00:00",
        "2026-10-15T11:30:00",
        "2026-10-15T12:00:00",
    ]
    assert sent["timeMin"] == "2026-10-15T10:00:00+02:00"


def test_slot_outside_business_hours_is_unavailable(monkeypatch):
    sent = {}
    _fake_freebusy(monkeypatch, [], sent)

    assert calendar.is_slot_available("2026-10-15T22:00:00", vertical="despacho") is False
    assert calendar.is_slot_available("2026-10-17T11:00:00", vertical="despacho") is False  # sábado
