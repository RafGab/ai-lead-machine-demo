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
