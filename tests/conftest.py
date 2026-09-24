import os
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# La base de datos se decide al importar backend.database, así que debe
# fijarse antes de importar la app. main.py monta rutas relativas al
# directorio raíz del repositorio.
os.environ["DATABASE_PATH"] = os.path.join(tempfile.mkdtemp(prefix="alm-tests-"), "test.db")
os.chdir(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402

NOTIFY_ENV_VARS = (
    "SMTP_USER", "SMTP_PASSWORD", "NOTIFY_EMAIL", "NOTIFY_DEMO_LEADS",
    "NOTIFY_EMAIL_EXTRANJERIA", "NOTIFY_EMAIL_DENTAL",
    "GOOGLE_CALENDAR_ID", "GOOGLE_CALENDAR_ID_EXTRANJERIA", "GOOGLE_CALENDAR_ID_DENTAL",
    "COMERCIAL_EMAIL", "COMERCIAL_EMAIL_EXTRANJERIA",
)

# Respuestas para preguntas abiertas (sin botones) al recorrer un rubro
# entero sin llamar a la IA.
OPEN_ANSWERS = {
    "name": "Carlos Ruiz", "phone": "+34 600 123 456", "email": "carlos@example.com",
    "reason": "dolor de muelas", "insurance_provider": "Sanitas", "preferred_date": "2026-10-05",
    "case_summary": "despido improcedente", "deadline_date": "2026-10-20",
    "check_in_date": "2026-11-01", "check_out_date": "2026-11-05", "special_request": "cuna",
    "address": "calle Mayor", "size_m2": 80, "current_country": "Perú", "nationality": "peruana",
    "max_price": 100000,
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """
    Cada test parte sin SMTP ni calendario configurados y sin poder
    llamar a OpenAI de verdad: si un test intenta usar la IA sin
    simularla, falla en vez de gastar dinero o depender de la red.
    """

    for name in NOTIFY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    def no_openai():
        raise AssertionError("Este test intentó llamar a OpenAI; simula la extracción.")

    monkeypatch.setattr("backend.demo.ai_helper.get_openai_client", no_openai)
    monkeypatch.setattr("backend.services.ai_service.get_openai_client", no_openai)


@pytest.fixture(autouse=True)
def blank_ai(monkeypatch):
    """
    Por defecto la "IA" no entiende nada (devuelve un lead vacío). Los
    tests que necesitan una extracción concreta la sustituyen ellos mismos.
    """

    from backend.demo.orchestrator import _find_model_cls
    from backend.demo.verticals import GENERIC_VERTICALS
    from backend.services.ai_service import AILeadData

    for module in GENERIC_VERTICALS.values():
        model_cls = _find_model_cls(module)
        monkeypatch.setattr(
            module, "extract",
            lambda message, conversation_history=None, _cls=model_cls: _cls(),
        )

    monkeypatch.setattr(
        "backend.services.conversation_service.extract_lead_data",
        lambda message, conversation_history=None: AILeadData(),
    )


@pytest.fixture
def sent_notifications(monkeypatch):
    """Captura los avisos por correo en vez de enviarlos."""

    sent = []

    def fake_send(subject, body, to=None):
        sent.append({"subject": subject, "body": body, "to": to})
        return True

    monkeypatch.setattr("backend.demo.lead_notification.send_notification", fake_send)
    monkeypatch.setattr("backend.routes.business_leads.send_notification", fake_send)

    return sent


@pytest.fixture
def client():
    return TestClient(app)


class Chat:
    """Pequeño ayudante para hablar con /demo/message."""

    def __init__(self, client, vertical, source="demo"):
        self.client = client
        self.vertical = vertical
        self.source = source
        self.conversation_id = None
        self.last = None

    def send(self, message, field=None, value=None):
        body = {
            "vertical": self.vertical,
            "message": message,
            "conversation_id": self.conversation_id,
            "source": self.source,
        }

        if field is not None:
            body["field"] = field
            body["value"] = value

        response = self.client.post("/demo/message", json=body)
        assert response.status_code == 200, response.text
        self.last = response.json()
        self.conversation_id = self.last["conversation_id"]

        return self.last

    @property
    def question(self):
        return (self.last.get("result") or {}).get("question")

    def complete(self, overrides=None):
        """Contesta todas las preguntas con botones o valores directos (sin IA)."""

        overrides = overrides or {}
        self.send("hola")

        for _ in range(25):
            question = self.question

            if not question:
                break

            field = question["field"]

            if field in overrides:
                value = overrides[field]
            elif question.get("options"):
                value = question["options"][0]["value"]
            else:
                value = OPEN_ANSWERS.get(field, "prueba")

            self.send(str(value), field=field, value=value)

        return self.last


@pytest.fixture
def chat(client):
    def make(vertical, source="demo"):
        return Chat(client, vertical, source)

    return make
