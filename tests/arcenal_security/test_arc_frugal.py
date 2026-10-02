from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch


def _load_core() -> ModuleType:
    name = "arcenal_arc_core"
    if name in sys.modules:
        return sys.modules[name]
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location(name, source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_core()


class CountingEngine:
    def __init__(self) -> None:
        self.calls = 0
        self.contexts: list[object] = []

    def execute(self, context: object, message: str):
        self.calls += 1
        self.contexts.append(context)
        return CORE.EngineOutput(response=f"Réponse {message}", usage={"input_tokens": 10, "output_tokens": 5, "cost": 0.02, "provider": "remote", "model": "small"})


def _context(agent_index: int = 0, request_context: dict[str, str] | None = None):
    agent = CORE.default_agents()[agent_index]
    caller = CORE.ApplicationIdentity(application_id=agent.application, user_id="test")
    return CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",))).build(agent, caller, None, request_context or {}, "demande")


def _model(identifier: str, capability: str, location: str = "remote", privacy: str = "admin", cost: float = 1.0):
    return CORE.ModelDescriptor(id=identifier, provider=location, model_name=identifier, capabilities=(CORE.CapabilityProfile(capability),), context_window=128_000, supports_tools=True, supports_structured_output=True, privacy_class=CORE.ConfidentialityLevel(privacy), location=CORE.ModelLocation(location), input_cost=cost, output_cost=cost, priority=10)


def _runtime_parts(tmp_path: Path, llm: CountingEngine):
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model("light", "light", cost=0.1))
    registry.upsert(_model("standard", "standard", cost=0.2))
    registry.upsert(_model("advanced", "advanced", cost=0.3))
    store = CORE.AutomationStore(tmp_path)
    metrics = CORE.FrugalMetricsRepository(tmp_path / "metrics.json")
    engine = CORE.FrugalAgentEngine(llm, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json", 0.5), CORE.WorkflowEngine(store), CORE.ModelRouter(registry), metrics, CORE.ProcessObserver(store))
    return engine, registry, store, metrics


def test_deterministic_path_avoids_llm_and_records_measurement(tmp_path: Path) -> None:
    llm = CountingEngine()
    engine, _registry, _store, metrics = _runtime_parts(tmp_path, llm)
    output = engine.execute(_context(), "Calcul 6 * 7")

    assert output.response == "Résultat : 42"
    assert output.usage["execution_mode"] == "deterministic"
    assert llm.calls == 0
    assert metrics.metrics().deterministic_hits == 1


def test_exact_and_semantic_cache_preserve_acl(tmp_path: Path) -> None:
    cache = CORE.FrugalCache(tmp_path / "cache.json", semantic_threshold=0.5)
    admin = _context()
    ats = _context(1)
    output = CORE.EngineOutput(response="Procédure validée", usage={"input_tokens": 8})
    cache.store(admin, "Quelle est la procédure de recrutement ?", output)
    cache.validate(cache.list()[0].id)

    assert cache.lookup(admin, "Comment fonctionne la procédure de recrutement ?") is not None
    assert cache.lookup(ats, "Quelle est la procédure de recrutement ?") is None


def test_cache_invalidation_removes_model_dependency(tmp_path: Path) -> None:
    cache = CORE.FrugalCache(tmp_path / "cache.json")
    output = CORE.EngineOutput(response="Réponse", usage={"registry_id": "small", "model": "small"})
    cache.store(_context(), "Question stable", output)

    assert cache.invalidate("model", "small") == 1
    assert cache.list() == ()


def test_router_selects_smallest_eligible_and_advanced_model(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model("light-costly", "light", cost=0.8))
    registry.upsert(_model("light-cheap", "light", cost=0.1))
    registry.upsert(_model("advanced", "advanced", cost=0.2))
    router = CORE.ModelRouter(registry)

    light = router.route(CORE.RoutingNeed(agent_id="arc", task_type=CORE.TaskType.GENERATION, required_capability=CORE.CapabilityProfile.LIGHT, confidentiality=CORE.ConfidentialityLevel.INTERNAL))
    advanced = router.route(CORE.RoutingNeed(agent_id="arc", task_type=CORE.TaskType.REASONING, required_capability=CORE.CapabilityProfile.ADVANCED, confidentiality=CORE.ConfidentialityLevel.INTERNAL))

    assert light.registry_id == "light-cheap"
    assert advanced.registry_id == "advanced"


def test_local_only_never_falls_back_to_remote(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model("remote", "standard"))
    need = CORE.RoutingNeed(agent_id="arc", task_type=CORE.TaskType.UNKNOWN, required_capability=CORE.CapabilityProfile.STANDARD, confidentiality=CORE.ConfidentialityLevel.INTERNAL, local_only=True)

    with pytest.raises(Exception, match="Aucun modèle activé"):
        CORE.ModelRouter(registry).route(need)


def test_global_provider_policy_cannot_be_bypassed(tmp_path: Path) -> None:
    registry = CORE.ModelRegistry(tmp_path / "models.json")
    registry.upsert(_model("remote", "standard"))
    need = CORE.RoutingNeed(agent_id="arc", task_type=CORE.TaskType.UNKNOWN, required_capability=CORE.CapabilityProfile.STANDARD, confidentiality=CORE.ConfidentialityLevel.INTERNAL)

    with pytest.raises(Exception, match="Aucun modèle activé"):
        CORE.ModelRouter(registry, denied_providers=("remote",)).route(need)


def test_empty_registry_compatibility_never_bypasses_local_only(tmp_path: Path) -> None:
    llm = CountingEngine()
    store = CORE.AutomationStore(tmp_path)
    engine = CORE.FrugalAgentEngine(llm, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), CORE.ModelRouter(CORE.ModelRegistry(tmp_path / "models.json")), CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store))
    context = _context().model_copy(update={"model_policy": CORE.ModelPolicy(local_only=True)})

    with pytest.raises(Exception, match="Aucun modèle n’est enregistré dans ARC"):
        engine.execute(context, "Rédige un message")
    assert llm.calls == 0


def test_empty_registry_never_falls_back_to_hermes_provider(tmp_path: Path) -> None:
    llm = CountingEngine()
    store = CORE.AutomationStore(tmp_path)
    router = CORE.ModelRouter(CORE.ModelRegistry(tmp_path / "models.json"))
    engine = CORE.FrugalAgentEngine(llm, CORE.DeterministicEngine(), CORE.FrugalCache(tmp_path / "cache.json"), CORE.WorkflowEngine(store), router, CORE.FrugalMetricsRepository(tmp_path / "metrics.json"), CORE.ProcessObserver(store))

    with pytest.raises(CORE.ModelRoutingError, match="Aucun modèle n’est enregistré dans ARC"):
        engine.execute(_context(), "Rédige un message")
    assert llm.calls == 0


def test_workflow_runs_without_llm_then_exception_falls_back(tmp_path: Path) -> None:
    llm = CountingEngine()
    engine, _registry, store, _metrics = _runtime_parts(tmp_path, llm)
    now = datetime.now(timezone.utc)
    workflow = CORE.AutomationWorkflow(id="demo", name="Démonstration", description="Retourne un statut structuré.", status=CORE.WorkflowStatus.ACTIVE, agent_id="arc", trigger="rapport stable", steps=(CORE.WorkflowStep(id="read", operation="structured_value", input_key="status"), CORE.WorkflowStep(id="format", operation="template", template="Statut : {result}")), autonomy="controlled", created_at=now, updated_at=now, approved_by="admin")
    store.save_workflow(workflow)

    handled = engine.execute(_context(request_context={"status": "OK"}), "rapport stable")
    fallback = engine.execute(_context(), "rapport stable")

    assert handled.response == "Statut : OK"
    assert handled.usage["execution_mode"] == "workflow"
    assert fallback.usage["execution_mode"] == "llm"
    assert llm.calls == 1


def test_agent_prompt_workflow_delegates_to_the_selected_agent_model(tmp_path: Path) -> None:
    llm = CountingEngine()
    engine, _registry, store, _metrics = _runtime_parts(tmp_path, llm)
    now = datetime.now(timezone.utc)
    workflow = CORE.AutomationWorkflow(id="incident", name="Incident", description="Analyse un incident.", status=CORE.WorkflowStatus.ACTIVE, agent_id="arc", trigger="incident déclaré", steps=(CORE.WorkflowStep(id="prompt", operation="agent_prompt", template="Analyse le serveur"),), autonomy="controlled", created_at=now, updated_at=now, approved_by="admin")
    store.save_workflow(workflow)

    output = engine.execute(_context(), "incident déclaré")

    assert output.response == "Réponse Analyse le serveur"
    assert output.usage["workflow_id"] == "incident"
    assert output.usage["execution_mode"] == "llm"
    assert llm.calls == 1


def test_workflow_cannot_escalate_permissions_or_tools(tmp_path: Path) -> None:
    store = CORE.AutomationStore(tmp_path)
    now = datetime.now(timezone.utc)
    workflow = CORE.AutomationWorkflow(id="unsafe", name="Interdit", description="Tente une élévation.", status=CORE.WorkflowStatus.ACTIVE, agent_id="ats", trigger="action", steps=(CORE.WorkflowStep(id="step", operation="status", template="OK", tool="arcenal-supervisor"),), permissions=("system.admin",), autonomy="controlled", created_at=now, updated_at=now, approved_by="admin")
    store.save_workflow(workflow)

    with pytest.raises(Exception, match="permissions absentes"):
        CORE.WorkflowEngine(store).execute(_context(1), "action")


def test_process_observer_only_creates_inactive_candidate(tmp_path: Path) -> None:
    store = CORE.AutomationStore(tmp_path)
    observer = CORE.ProcessObserver(store, threshold=2)
    context = _context(request_context={"status": "OK"})

    assert observer.observe(context, (), "OK") is None
    candidate = observer.observe(context, (), "OK")

    assert candidate is not None
    assert candidate.reviewed is False
    assert store.workflows() == ()


def test_measured_baseline_is_required_for_avoided_tokens(tmp_path: Path) -> None:
    repository = CORE.FrugalMetricsRepository(tmp_path / "metrics.json")
    assert repository.baseline("arc", CORE.TaskType.GENERATION) is None
    repository.record(CORE.ExecutionMeasurement(request_id="1", agent_id="arc", task_type=CORE.TaskType.GENERATION, execution_mode=CORE.ExecutionMode.LLM, input_tokens=90, output_tokens=10, estimated_cost=0.4, duration_ms=50, created_at=datetime.now(timezone.utc)))

    assert repository.baseline("arc", CORE.TaskType.GENERATION) == (100, 0.4)


def test_cache_saving_uses_observed_llm_baseline(tmp_path: Path) -> None:
    llm = CountingEngine()
    engine, _registry, _store, metrics = _runtime_parts(tmp_path, llm)
    context = _context()

    before = engine.execute(context, "Rédige un bref message")
    after = engine.execute(context, "Rédige un bref message")

    assert before.usage["execution_mode"] == "llm"
    assert after.usage["execution_mode"] == "cache"
    assert metrics.recent()[1].tokens_avoided_estimate == 15
    assert metrics.recent()[1].estimated_cost_avoided == 0.02
    assert metrics.metrics().by_provider == {"remote": 1}
    assert llm.calls == 1


def test_routing_latency_is_measured_without_network(tmp_path: Path) -> None:
    llm = CountingEngine()
    engine, _registry, _store, metrics = _runtime_parts(tmp_path, llm)
    engine.execute(_context(), "Rédige un bref message")

    measurement = metrics.recent()[0]
    assert measurement.routing_duration_ms >= 0
    assert measurement.duration_ms >= measurement.routing_duration_ms


def _api_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "frugal_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_frugal_api_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("L'API ARC Frugal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_frugal_api_requires_admin_and_validates_registry(tmp_path: Path) -> None:
    app = FastAPI()
    app.include_router(_api_module().router)
    client = TestClient(app)
    payload = {"provider": "ollama", "model_name": "qwen", "enabled": True, "capabilities": ["light"], "context_window": 8192, "supports_tools": False, "supports_structured_output": True, "supports_vision": False, "privacy_class": "confidential", "location": "local", "hosting_region": "France", "input_cost": 0, "output_cost": 0, "priority": 5}
    provider_payload = {"name": "Ollama", "type": "ollama", "enabled": True, "base_url": "http://127.0.0.1:11434/v1", "authentication_type": "none", "secret_reference": None, "location": "local", "jurisdiction": "France", "capabilities": ["chat", "tool_calling"], "priority": 5, "health": "unknown"}
    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path), "ARCENAL_AUDIT_DIR": str(tmp_path / "audit")}):
        assert client.get("/frugal/v1/overview").status_code == 401
        saved_provider = client.put("/frugal/v1/providers/ollama", headers={"Remote-User": "admin"}, json=provider_payload)
        saved = client.put("/frugal/v1/models/qwen-local", headers={"Remote-User": "admin"}, json=payload)
        overview = client.get("/frugal/v1/overview", headers={"Remote-User": "admin"})

    assert saved_provider.status_code == 200
    assert saved.status_code == 200
    ollama = next(item for item in overview.json()["providers"] if item["id"] == "ollama")
    assert ollama["secret_reference"] is None
    assert overview.json()["models"][0]["location"] == "local"
