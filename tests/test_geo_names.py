import pytest

from backend.demo.orchestrator import _find_model_cls
from backend.demo.verticals import GENERIC_VERTICALS
from backend.services import geo_names, sanitize

EXTRANJERIA = GENERIC_VERTICALS["extranjeria"]
LEAD_CLS = _find_model_cls(EXTRANJERIA)


@pytest.mark.parametrize("typed,expected", [
    ("peru", "Perú"), ("PERÚ", "Perú"), ("  colombia ", "Colombia"), ("mexico", "México"),
    ("Mejico", "México"), ("republica dominicana", "República Dominicana"),
    ("EEUU", "Estados Unidos"), ("EE.UU.", "Estados Unidos"), ("españa", "España"),
    ("corea del sur", "Corea del Sur"), ("guinea ecuatorial", "Guinea Ecuatorial"),
])
def test_country_is_written_correctly(typed, expected):
    assert geo_names.normalize_country(typed) == expected


def test_unknown_country_is_only_tidied_and_never_replaced_by_a_similar_one():
    assert geo_names.normalize_country("niger") == "Niger", "No debe confundirse con Nigeria"


def test_long_answers_are_left_alone():
    sentence = "vivo en un pueblo pequeño cerca de lima peru"

    assert geo_names.normalize_country(sentence) == sentence
    assert geo_names.normalize_nationality(sentence) == sentence


@pytest.mark.parametrize("typed,expected", [
    ("colombiansa", "Colombiana"), ("venzolana", "Venezolana"), ("PERUANA", "Peruana"),
    ("peruano", "Peruano"), ("nicaraguense", "Nicaragüense"), ("marroqui", "Marroquí"),
    ("peruana y española", "Peruana y Española"),
])
def test_nationality_fixes_typos_and_keeps_the_gender_typed(typed, expected):
    assert geo_names.normalize_nationality(typed) == expected


def test_country_typed_as_nationality_is_kept_as_a_country_not_turned_into_a_guessed_gender():
    assert geo_names.normalize_nationality("colombia") == "Colombia"


@pytest.mark.parametrize("typed", ["colombiana", "Colombiano", "colombia", "colombiansa"])
def test_stats_group_collapses_every_way_of_writing_the_same_nationality(typed):
    assert geo_names.nationality_group(typed) == "Colombiano/a"


def test_group_for_stats_only_touches_country_and_nationality():
    assert geo_names.group_for_stats("current_country", "peru") == "Perú"
    assert geo_names.group_for_stats("nationality", "peruana") == "Peruano/a"
    assert geo_names.group_for_stats("procedure", "estancia por estudios") == "estancia por estudios"


def test_clean_extracted_normalizes_country_and_nationality_on_save():
    cleaned, _ = sanitize.clean_extracted(
        {"current_country": "peru", "nationality": "colombiansa", "city": "León"}, "vivo en peru"
    )

    assert cleaned["current_country"] == "Perú"
    assert cleaned["nationality"] == "Colombiana"
    assert cleaned["city"] == "León"


def test_lead_is_stored_with_clean_country_and_nationality(chat, monkeypatch):
    monkeypatch.setattr(
        EXTRANJERIA, "extract",
        lambda message, conversation_history=None: LEAD_CLS(current_country="peru", nationality="colombiansa"),
    )
    conversation = chat("extranjeria")
    conversation.send("hola")
    conversation.send("Ana", field="name", value="Ana")

    reply = conversation.send("vivo en peru y soy colombiansa")

    assert reply["lead"]["current_country"] == "Perú"
    assert reply["lead"]["nationality"] == "Colombiana"


def test_repeating_a_known_value_in_another_spelling_is_not_treated_as_new_information(chat, monkeypatch):
    conversation = chat("extranjeria")
    conversation.send("hola")
    conversation.send("Ana", field="name", value="Ana")
    monkeypatch.setattr(
        EXTRANJERIA, "extract",
        lambda message, conversation_history=None: LEAD_CLS(current_country="peru"),
    )
    conversation.send("vivo en peru")
    monkeypatch.setattr(
        EXTRANJERIA, "extract",
        lambda message, conversation_history=None: LEAD_CLS(current_country="PERU"),
    )

    reply = conversation.send("blablabla")

    assert reply["assistant_message"].startswith("No estoy seguro de haber entendido eso")


def test_insights_count_the_same_country_written_differently_as_one(client, chat, monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "clave-de-prueba")
    # Datos antiguos, guardados sin normalizar (como los que ya hay en producción).
    for country in ("peru", "Perú", "PERU"):
        conversation = chat("despacho", source="widget")
        conversation.complete({"name": f"Persona {country}"})

    from backend.database.database import get_connection
    import json

    connection = get_connection()
    rows = connection.execute(
        "SELECT id, lead_data FROM demo_conversations WHERE vertical = 'despacho' AND source = 'widget'"
    ).fetchall()

    for row in rows:
        lead = json.loads(row["lead_data"])
        lead["current_country"] = {"Persona peru": "peru", "Persona Perú": "Perú", "Persona PERU": "PERU"}.get(lead["name"])
        connection.execute(
            "UPDATE demo_conversations SET lead_data = ? WHERE id = ?", (json.dumps(lead, ensure_ascii=False), row["id"])
        )

    connection.commit()
    connection.close()

    data = client.get("/admin/insights-demo?vertical=despacho&key=clave-de-prueba").json()
    country = next(field for field in data["fields"] if field["field"] == "current_country")

    assert country["top_values"] == [["Perú", 3]]
