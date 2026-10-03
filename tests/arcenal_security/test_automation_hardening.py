from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest


def _load_core() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "arc_core" / "__init__.py"
    spec = importlib.util.spec_from_file_location("arcenal_arc_core", source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = sys.modules.get(spec.name) or importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_core()


def _load_frugal_api() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "frugal_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_frugal_api_hardening_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("L’API ARC Frugal est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _scheduled_workflow(status: CORE.WorkflowStatus) -> CORE.AutomationWorkflow:
    now = datetime.now(timezone.utc)
    return CORE.AutomationWorkflow(
        id="rapport-quotidien",
        name="Rapport quotidien",
        description="Analyse les services",
        status=status,
        agent_id="arc",
        profile_name="default",
        trigger="Planification : every day 8am",
        schedule="every day 8am",
        steps=(CORE.WorkflowStep(id="response", operation="agent_prompt", template="Analyse les services"),),
        autonomy="controlled",
        created_at=now,
        updated_at=now,
        approved_by="admin" if status is CORE.WorkflowStatus.ACTIVE else None,
    )


def test_scheduled_workflow_never_matches_a_conversation(tmp_path: Path) -> None:
    store = CORE.AutomationStore(tmp_path)
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE)
    store.save_workflow(workflow)
    context = type("Context", (), {"agent": type("Agent", (), {"id": "arc"})()})()

    assert CORE.WorkflowEngine(store)._matches(workflow, context, workflow.trigger) is False


def test_active_transition_records_human_approval() -> None:
    workflow = _scheduled_workflow(CORE.WorkflowStatus.TESTING)

    active = CORE.transition_workflow(workflow, CORE.WorkflowStatus.ACTIVE, "admin@example.test")

    assert active.approved_by == "admin@example.test"
    assert active.status is CORE.WorkflowStatus.ACTIVE


def test_schedule_contract_is_persisted_without_cron_job() -> None:
    workflow = _scheduled_workflow(CORE.WorkflowStatus.DRAFT)

    assert workflow.schedule == "every day 8am"
    assert workflow.cron_job_id is None
    assert workflow.profile_name == "default"


def test_approval_creates_the_executable_cron_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.TESTING)
    approved = CORE.transition_workflow(workflow, CORE.WorkflowStatus.ACTIVE, "admin@example.test")
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: "123456789abc")

    synchronized = api._synchronize_scheduled_workflow(workflow, approved)

    assert synchronized.cron_job_id == "123456789abc"
    assert synchronized.approved_by == "admin@example.test"


def test_disabling_an_approved_workflow_pauses_its_cron_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    current = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(update={"cron_job_id": "123456789abc"})
    disabled = CORE.transition_workflow(current, CORE.WorkflowStatus.DISABLED, "admin@example.test")
    observed: list[tuple[str, CORE.WorkflowStatus]] = []
    monkeypatch.setattr(api, "_update_cron_state", lambda workflow, status: observed.append((workflow.cron_job_id, status)))

    api._synchronize_scheduled_workflow(current, disabled)

    assert observed == [("123456789abc", CORE.WorkflowStatus.DISABLED)]
