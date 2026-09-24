import pytest

from backend.demo.orchestrator import _find_model_cls
from backend.demo.verticals import GENERIC_VERTICALS

ALL_VERTICALS = list(GENERIC_VERTICALS)


@pytest.mark.parametrize("vertical", ALL_VERTICALS)
def test_every_vertical_can_be_completed_and_offers_booking(chat, vertical):
    conversation = chat(vertical)
    reply = conversation.complete()

    assert reply["result"]["status"] == "completed"
    assert reply["result"]["booking_available"] is True
    assert reply["options"] is None


@pytest.mark.parametrize("vertical", ALL_VERTICALS)
def test_follow_up_after_completion_is_a_real_reply_not_a_static_one(chat, monkeypatch, vertical):
    monkeypatch.setattr(
        "backend.demo.orchestrator.generate_followup_reply",
        lambda prompt, message, conversation_history=None: f"respuesta a: {message}",
    )
    conversation = chat(vertical)
    conversation.complete()

    first = conversation.send("¿cuánto tarda?")
    second = conversation.send("¿y dónde están?")

    assert first["assistant_message"] == "respuesta a: ¿cuánto tarda?"
    assert second["assistant_message"] == "respuesta a: ¿y dónde están?"
    assert second["result"]["status"] == "completed"
    assert second["result"]["booking_available"] is True


def test_follow_up_failure_returns_a_friendly_message_not_an_error(chat, monkeypatch):
    def broken(prompt, message, conversation_history=None):
        raise RuntimeError("OpenAI caído")

    monkeypatch.setattr("backend.demo.orchestrator.generate_followup_reply", broken)
    conversation = chat("extranjeria")
    conversation.complete()

    reply = conversation.send("¿cuánto tarda el proceso?")

    assert "Inténtalo de nuevo" in reply["assistant_message"]


@pytest.mark.parametrize("vertical", ALL_VERTICALS)
def test_message_nobody_understands_is_acknowledged_and_question_is_repeated(chat, vertical):
    conversation = chat(vertical)
    conversation.send("hola")
    pending_field = conversation.question["field"]

    reply = conversation.send("blablabla")

    assert reply["assistant_message"].startswith("No estoy seguro de haber entendido eso")
    assert reply["result"]["question"]["field"] == pending_field


def test_first_greeting_is_not_treated_as_a_misunderstanding(chat):
    conversation = chat("extranjeria")
    reply = conversation.send("hola")

    assert not reply["assistant_message"].startswith("No estoy seguro")


def test_data_volunteered_early_is_kept_and_asked_only_once(chat, monkeypatch):
    module = GENERIC_VERTICALS["extranjeria"]
    model_cls = _find_model_cls(module)
    monkeypatch.setattr(
        module, "extract",
        lambda message, conversation_history=None: model_cls(
            name="Ana", current_country="Colombia", nationality="colombiana"
        ),
    )
    conversation = chat("extranjeria")

    reply = conversation.send("Soy Ana, vivo en Colombia y soy colombiana")

    assert reply["lead"]["name"] == "Ana"
    assert reply["result"]["question"]["field"] == "education_level"


def test_correction_replaces_old_value_and_keeps_the_rest(chat, monkeypatch):
    module = GENERIC_VERTICALS["extranjeria"]
    model_cls = _find_model_cls(module)
    conversation = chat("extranjeria")
    conversation.send("hola")
    conversation.send("Carlos", field="name", value="Carlos")
    conversation.send("Perú", field="current_country", value="Perú")

    monkeypatch.setattr(
        module, "extract",
        lambda message, conversation_history=None: model_cls(name="Pedro"),
    )
    reply = conversation.send("en realidad me llamo Pedro")

    assert reply["lead"]["name"] == "Pedro"
    assert reply["lead"]["current_country"] == "Perú"


@pytest.mark.parametrize("phrase", ["no gracias", "Adiós", "eso es todo!", "chao"])
def test_closing_message_ends_the_conversation_without_the_ai(chat, phrase):
    conversation = chat("dental")
    conversation.send("hola")

    reply = conversation.send(phrase)

    assert reply["result"]["status"] == "closed"


def test_temporary_ai_failure_is_retried(chat, monkeypatch):
    module = GENERIC_VERTICALS["extranjeria"]
    model_cls = _find_model_cls(module)
    calls = {"count": 0}

    def flaky(message, conversation_history=None):
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("fallo de red")
        return model_cls(name="Ana")

    monkeypatch.setattr(module, "extract", flaky)
    monkeypatch.setattr("backend.demo.orchestrator.time.sleep", lambda seconds: None)
    conversation = chat("extranjeria")

    reply = conversation.send("Ana")

    assert calls["count"] == 3
    assert reply["lead"]["name"] == "Ana"


def test_persistent_ai_failure_returns_an_error_message_not_a_500(chat, monkeypatch):
    module = GENERIC_VERTICALS["extranjeria"]

    def down(message, conversation_history=None):
        raise RuntimeError("OpenAI caído")

    monkeypatch.setattr(module, "extract", down)
    monkeypatch.setattr("backend.demo.orchestrator.time.sleep", lambda seconds: None)
    conversation = chat("extranjeria")

    reply = conversation.send("Ana")

    assert reply["result"]["status"] == "error"
    assert "Inténtalo de nuevo" in reply["assistant_message"]


def test_unknown_vertical_and_conversation_are_rejected_with_400(client):
    unknown_vertical = client.post("/demo/message", json={"vertical": "no-existe", "message": "hola"})
    unknown_conversation = client.post(
        "/demo/message",
        json={"vertical": "extranjeria", "message": "hola", "conversation_id": 999999},
    )

    assert unknown_vertical.status_code == 400
    assert unknown_conversation.status_code == 400
