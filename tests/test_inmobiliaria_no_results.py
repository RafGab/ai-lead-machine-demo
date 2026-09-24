from backend.database.database import get_connection
from backend.services.matching import get_available_cities


def _min_price(city, operation, property_type):
    connection = get_connection()
    row = connection.execute(
        "SELECT MIN(price) FROM properties WHERE available = 1 AND city = ? "
        "AND operation = ? AND property_type = ?",
        (city, operation, property_type),
    ).fetchone()
    connection.close()
    return row[0]


def _no_results_chat(chat):
    """Compra en una ciudad con un presupuesto por debajo del mínimo del catálogo."""

    city = get_available_cities()[0]
    minimum = None

    for candidate in get_available_cities():
        minimum = _min_price(candidate, "venta", "vivienda")
        if minimum:
            city = candidate
            break

    assert minimum, "El catálogo de prueba debería tener alguna vivienda en venta."

    conversation = chat("inmobiliaria")
    conversation.complete({
        "operation": "compra", "property_type": "vivienda", "city": city,
        "max_price": minimum - 1000,
    })

    return conversation, city, minimum


def test_no_results_offers_quick_reply_buttons(chat):
    conversation, city, minimum = _no_results_chat(chat)
    result = conversation.last["result"]

    assert result["status"] == "no_results"
    assert conversation.last["options_field"] == "_retry"

    values = [option["value"] for option in conversation.last["options"]]
    assert f"raise:{int(minimum)}" in values
    assert "budget" in values and "city" in values


def test_ambiguous_yes_does_not_repeat_the_same_message(chat):
    conversation, _, _ = _no_results_chat(chat)
    first_message = conversation.last["assistant_message"]

    reply = conversation.send("Sí")

    assert reply["assistant_message"] != first_message
    assert "No estoy seguro" in reply["assistant_message"]
    assert reply["options"], "Debe volver a ofrecer los botones para elegir."


def test_raise_budget_button_finds_matches(chat):
    conversation, _, minimum = _no_results_chat(chat)

    reply = conversation.send("Subir", field="_retry", value=f"raise:{int(minimum)}")

    assert reply["result"]["status"] == "matches_found"
    assert reply["lead"]["max_price"] == float(int(minimum))


def test_widen_budget_button_asks_for_budget_again(chat):
    conversation, city, _ = _no_results_chat(chat)

    reply = conversation.send("Ampliar", field="_retry", value="budget")

    assert reply["lead"]["max_price"] is None
    assert reply["lead"]["city"] == city
    assert reply["options_field"] == "max_price"


def test_other_city_button_asks_for_city_with_options(chat):
    conversation, _, _ = _no_results_chat(chat)

    reply = conversation.send("Otra", field="_retry", value="city")

    assert reply["lead"]["city"] is None
    assert reply["options_field"] == "city"
    assert {option["value"] for option in reply["options"]} == set(get_available_cities())


def test_city_without_properties_offers_the_available_cities(chat):
    conversation = chat("inmobiliaria")
    reply = conversation.complete({
        "operation": "compra", "property_type": "vivienda", "city": "Zamora",
    })

    assert reply["result"]["status"] == "no_results"
    assert "Zamora" in reply["assistant_message"]
    assert reply["options_field"] == "city"
    assert {option["value"] for option in reply["options"]} == set(get_available_cities())
