from __future__ import annotations

import importlib
import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _load(name: str, filename: str) -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / filename
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Le module {filename} est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


AGENTS = _load("arcenal_agents_api", "agents_api.py")
MODULE = _load("arcenal_chat_api_test", "chat_api.py")
AgentExecutionError = importlib.import_module("arcenal_arc_core.errors").AgentExecutionError


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(MODULE.router, prefix="/api/plugins/arcenal-supervisor")
    return TestClient(app)


class ArcChatApiTests(TestCase):
    def test_session_round_trip_and_archive_are_persistent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "chat-sessions.json"
            with patch.object(MODULE, "_store_path", return_value=store):
                client = _client()
                created = client.post("/api/plugins/arcenal-supervisor/chat/sessions")
                listed = client.get("/api/plugins/arcenal-supervisor/chat/sessions")
                archived = client.patch(
                    f"/api/plugins/arcenal-supervisor/chat/sessions/{created.json()['id']}",
                    json={"archived": True},
                )
                remaining = client.get("/api/plugins/arcenal-supervisor/chat/sessions")

            self.assertEqual(created.status_code, 201)
            self.assertEqual(len(listed.json()), 1)
            self.assertTrue(archived.json()["archived"])
            self.assertEqual(remaining.json(), [])
            self.assertEqual(store.stat().st_mode & 0o777, 0o600)

    def test_message_uses_arc_core_and_persists_both_roles(self) -> None:
        result = SimpleNamespace(response="Réponse ARC", sources=(), actions=(), usage={"provider": "openrouter"})
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "chat-sessions.json"
            with patch.object(MODULE, "_store_path", return_value=store), patch.object(MODULE, "_agents", return_value=AGENTS), patch.object(AGENTS, "query_dashboard_agent", return_value=result) as query:
                client = _client()
                session = client.post("/api/plugins/arcenal-supervisor/chat/sessions").json()
                response = client.post(
                    f"/api/plugins/arcenal-supervisor/chat/sessions/{session['id']}/messages",
                    headers={"Remote-User": "admin@example.org"},
                    json={"text": "Analyse le serveur"},
                )

            self.assertEqual(response.status_code, 200)
            self.assertEqual([item["role"] for item in response.json()["session"]["messages"]], ["user", "assistant"])
            self.assertEqual(response.json()["usage"]["provider"], "openrouter")
            query.assert_called_once_with("arc", "Analyse le serveur", session["id"], "admin@example.org")

    def test_message_requires_the_yunohost_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.object(MODULE, "_store_path", return_value=Path(directory) / "chat-sessions.json"), patch.object(MODULE, "_agents", return_value=AGENTS):
            client = _client()
            session = client.post("/api/plugins/arcenal-supervisor/chat/sessions").json()
            response = client.post(
                f"/api/plugins/arcenal-supervisor/chat/sessions/{session['id']}/messages",
                json={"text": "Bonjour"},
            )

        self.assertEqual(response.status_code, 401)

    def test_provider_failure_keeps_the_user_message_for_diagnosis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "chat-sessions.json"
            failure = AgentExecutionError("Fournisseur indisponible")
            with patch.object(MODULE, "_store_path", return_value=store), patch.object(MODULE, "_agents", return_value=AGENTS), patch.object(AGENTS, "query_dashboard_agent", side_effect=failure):
                client = _client()
                session = client.post("/api/plugins/arcenal-supervisor/chat/sessions").json()
                response = client.post(
                    f"/api/plugins/arcenal-supervisor/chat/sessions/{session['id']}/messages",
                    headers={"Remote-User": "admin@example.org"},
                    json={"text": "Bonjour"},
                )
                persisted = client.get(f"/api/plugins/arcenal-supervisor/chat/sessions/{session['id']}")

            self.assertEqual(response.status_code, 503)
            self.assertEqual([item["role"] for item in persisted.json()["messages"]], ["user"])
