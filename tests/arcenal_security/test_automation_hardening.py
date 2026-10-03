from __future__ import annotations

import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from cron.jobs import parse_schedule


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


def _admin_request() -> Request:
    return Request({"type": "http", "headers": [(b"remote-user", b"admin@example.test")]})


class _FailingWorkflowStore:
    def __init__(self, workflow: CORE.AutomationWorkflow) -> None:
        self.workflow = workflow

    def workflows(self) -> tuple[CORE.AutomationWorkflow, ...]:
        return (self.workflow,)

    def save_workflow(self, _workflow: CORE.AutomationWorkflow) -> CORE.AutomationWorkflow:
        raise CORE.FrugalStorageError("Persistance indisponible.")


class _WorkflowStore:
    def __init__(self, workflow: CORE.AutomationWorkflow) -> None:
        self.workflow = workflow

    def workflows(self) -> tuple[CORE.AutomationWorkflow, ...]:
        return (self.workflow,)

    def save_workflow(self, workflow: CORE.AutomationWorkflow) -> CORE.AutomationWorkflow:
        self.workflow = workflow
        return workflow


class _MutableWorkflowStore:
    def __init__(self) -> None:
        self.values: tuple[CORE.AutomationWorkflow, ...] = ()

    def workflows(self) -> tuple[CORE.AutomationWorkflow, ...]:
        return self.values

    def save_workflow(self, workflow: CORE.AutomationWorkflow) -> CORE.AutomationWorkflow:
        self.values = (*self.values, workflow)
        return workflow


def _workflow_payload() -> dict[str, object]:
    workflow = _scheduled_workflow(CORE.WorkflowStatus.DRAFT)
    excluded = {"status", "created_at", "updated_at", "approved_by"}
    return workflow.model_dump(mode="json", exclude=excluded)


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


def test_late_execution_counter_never_restores_a_disabled_workflow(tmp_path: Path) -> None:
    store = CORE.AutomationStore(tmp_path)
    active = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE)
    disabled = active.model_copy(update={"status": CORE.WorkflowStatus.DISABLED})
    store.save_workflow(disabled)

    store.record_execution(active.id)

    persisted = store.workflows()[0]
    assert persisted.status is CORE.WorkflowStatus.DISABLED
    assert persisted.executions == 0


def test_schedule_contract_is_persisted_without_cron_job() -> None:
    workflow = _scheduled_workflow(CORE.WorkflowStatus.DRAFT)

    assert workflow.schedule == "every day 8am"
    assert workflow.cron_job_id is None
    assert workflow.profile_name == "default"


def test_concurrent_creation_rejects_duplicate_workflow_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    api = _load_frugal_api()
    store = _MutableWorkflowStore()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api.CORE, "append_agent_event", lambda *_args: None)

    def create(_index: int) -> int:
        try:
            api.create_workflow(_admin_request(), _workflow_payload())
        except HTTPException as exc:
            return exc.status_code
        return 201

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(create, range(2)))

    assert statuses == [201, 409]
    assert len(store.workflows()) == 1


def test_approval_creates_the_executable_cron_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.TESTING)
    approved = CORE.transition_workflow(workflow, CORE.WorkflowStatus.ACTIVE, "admin@example.test")
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: "123456789abc")

    synchronized = api._synchronize_scheduled_workflow(workflow, approved)

    assert synchronized.cron_job_id == "123456789abc"
    assert synchronized.approved_by == "admin@example.test"


def test_cron_is_prepared_dormant_and_paused_before_linking(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE)
    observed: list[tuple[str, str]] = []
    dashboard = SimpleNamespace(
        _create_cron_job_sync=lambda body, profile: observed.append((body.schedule, profile)) or {"id": "dormant-cron"},
        _pause_cron_job_sync=lambda job_id, profile: observed.append((job_id, profile)),
        _delete_cron_job_sync=lambda *_args: None,
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    job_id = api._create_cron_job(workflow)

    assert job_id == "dormant-cron"
    assert observed == [(api.DORMANT_CRON_SCHEDULE, "default"), ("dormant-cron", "default")]


def test_disabling_an_approved_workflow_pauses_its_cron_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    current = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(update={"cron_job_id": "123456789abc"})
    disabled = CORE.transition_workflow(current, CORE.WorkflowStatus.DISABLED, "admin@example.test")
    observed: list[tuple[str, str]] = []
    dashboard = SimpleNamespace(_pause_cron_job_sync=lambda job_id, profile: observed.append((job_id, profile)))
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    api._synchronize_scheduled_workflow(current, disabled)

    assert observed == [("123456789abc", "default")]


def test_archive_pauses_before_persistence_then_deletes_after_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    current = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(update={"cron_job_id": "123456789abc"})
    archived = CORE.transition_workflow(current, CORE.WorkflowStatus.ARCHIVED, "admin@example.test")
    observed: list[str] = []
    dashboard = SimpleNamespace(
        _pause_cron_job_sync=lambda *_args: observed.append("pause"),
        _delete_cron_job_sync=lambda *_args: observed.append("delete"),
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    synchronized = api._synchronize_scheduled_workflow(current, archived)
    api._finalize_scheduled_workflow(synchronized)

    assert observed == ["pause", "delete"]


def test_activation_recreates_a_missing_managed_cron_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    current = _scheduled_workflow(CORE.WorkflowStatus.TESTING).model_copy(update={"cron_job_id": "missing-cron"})
    active = CORE.transition_workflow(current, CORE.WorkflowStatus.ACTIVE, "admin@example.test")
    def missing_job(*_args: object) -> None:
        raise api.HTTPException(status_code=404)

    dashboard = SimpleNamespace(_get_cron_job_sync=missing_job)
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: "replacement-cron")

    synchronized = api._synchronize_scheduled_workflow(current, active)

    assert synchronized.cron_job_id == "replacement-cron"


def test_activation_removes_created_cron_when_persistence_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    store = _FailingWorkflowStore(_scheduled_workflow(CORE.WorkflowStatus.TESTING))
    deleted: list[tuple[str, str]] = []
    dashboard = SimpleNamespace(_delete_cron_job_sync=lambda job_id, profile: deleted.append((job_id, profile)))
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: "orphan-candidate")
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api.CORE, "append_agent_event", lambda *_args: None)

    with pytest.raises(HTTPException) as raised:
        api.change_workflow(store.workflow.id, api.WorkflowTransition(status="active"), _admin_request())

    assert raised.value.status_code == 500
    assert deleted == [("orphan-candidate", "default")]


def test_scheduler_failure_keeps_workflow_in_testing_and_is_audited(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    store = _WorkflowStore(_scheduled_workflow(CORE.WorkflowStatus.TESTING))
    events: list[str] = []
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: (_ for _ in ()).throw(RuntimeError("scheduler")))
    monkeypatch.setattr(api.CORE, "append_agent_event", lambda event, *_args: events.append(event))

    with pytest.raises(HTTPException):
        api.change_workflow(store.workflow.id, api.WorkflowTransition(status="active"), _admin_request())

    assert store.workflow.status is CORE.WorkflowStatus.TESTING
    assert events == ["frugal.workflow.transition.failed"]


def test_audit_failure_rolls_back_persistence_and_created_cron(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    store = _WorkflowStore(_scheduled_workflow(CORE.WorkflowStatus.TESTING))
    deleted: list[str] = []
    calls = 0
    def audit(*_args: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("audit")
    dashboard = SimpleNamespace(_delete_cron_job_sync=lambda job_id, _profile: deleted.append(job_id))
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: "rollback-cron")
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api.CORE, "append_agent_event", audit)

    with pytest.raises(HTTPException):
        api.change_workflow(store.workflow.id, api.WorkflowTransition(status="active"), _admin_request())

    assert store.workflow.status is CORE.WorkflowStatus.TESTING
    assert deleted == ["rollback-cron"]


def test_concurrent_activation_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    store = _WorkflowStore(_scheduled_workflow(CORE.WorkflowStatus.TESTING))
    created: list[str] = []
    dashboard = SimpleNamespace(
        _get_cron_job_sync=lambda *_args: {"id": "single-cron"},
        _update_cron_job_sync=lambda *_args: None,
        _resume_cron_job_sync=lambda *_args: None,
    )
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api, "_create_cron_job", lambda _workflow: created.append("single-cron") or "single-cron")
    monkeypatch.setattr(api.CORE, "append_agent_event", lambda *_args: None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(lambda _index: api.change_workflow(store.workflow.id, api.WorkflowTransition(status="active"), _admin_request()), range(2)))

    assert len(results) == 2
    assert store.workflow.status is CORE.WorkflowStatus.ACTIVE
    assert created == ["single-cron"]


def test_restart_reconciliation_removes_orphan_and_repairs_active_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(update={"cron_job_id": "linked-cron"})
    store = _WorkflowStore(workflow)
    updated: list[str] = []
    resumed: list[str] = []
    deleted: list[str] = []
    dashboard = SimpleNamespace(
        _list_cron_jobs_sync=lambda _profile: [
            {"id": "linked-cron", "name": f"{api.MANAGED_CRON_PREFIX}{workflow.id}:Rapport"},
            {"id": "orphan-cron", "name": f"{api.MANAGED_CRON_PREFIX}absent:Orpheline"},
        ],
        _update_cron_job_sync=lambda job_id, *_args: updated.append(job_id),
        _resume_cron_job_sync=lambda job_id, _profile: resumed.append(job_id),
        _delete_cron_job_sync=lambda job_id, _profile: deleted.append(job_id),
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    api._reconcile_scheduled_workflows(store)

    assert updated == ["linked-cron"]
    assert resumed == ["linked-cron"]
    assert deleted == ["orphan-cron"]


def test_reconciliation_does_not_reschedule_healthy_active_job(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(
        update={"cron_job_id": "linked-cron", "schedule": "30m"}
    )
    store = _WorkflowStore(workflow)
    dashboard = SimpleNamespace(
        _list_cron_jobs_sync=lambda _profile: [{
            "id": "linked-cron",
            "name": f"{api.MANAGED_CRON_PREFIX}{workflow.id}:Rapport",
            "schedule": parse_schedule("30m"),
            "schedule_display": "every 30m",
            "enabled": True,
            "state": "scheduled",
        }],
        _update_cron_job_sync=lambda *_args: pytest.fail("Le cron sain ne doit pas être replanifié."),
        _resume_cron_job_sync=lambda *_args: pytest.fail("Le cron sain ne doit pas être repris."),
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    api._reconcile_scheduled_workflows(store)


def test_reconciliation_keeps_existing_relative_one_shot_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(
        update={"cron_job_id": "linked-cron", "schedule": "in 30m"}
    )
    store = _WorkflowStore(workflow)
    job_schedule = parse_schedule("in 30m")
    dashboard = SimpleNamespace(
        _list_cron_jobs_sync=lambda _profile: [{
            "id": "linked-cron",
            "name": f"{api.MANAGED_CRON_PREFIX}{workflow.id}:Rapport",
            "schedule": job_schedule,
            "enabled": True,
            "state": "scheduled",
        }],
        _update_cron_job_sync=lambda *_args: pytest.fail("L’échéance relative existante ne doit pas être repoussée."),
        _resume_cron_job_sync=lambda *_args: pytest.fail("Le cron actif ne doit pas être repris."),
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    api._reconcile_scheduled_workflows(store)
    api._reconcile_scheduled_workflows(store)

    assert store.workflow.schedule == job_schedule["run_at"]


def test_activation_materializes_relative_one_shot_schedule() -> None:
    api = _load_frugal_api()
    draft = _scheduled_workflow(CORE.WorkflowStatus.DRAFT).model_copy(update={"schedule": "in 30m"})
    testing = CORE.transition_workflow(draft, CORE.WorkflowStatus.TESTING, "admin@example.test")
    active = CORE.transition_workflow(testing, CORE.WorkflowStatus.ACTIVE, "admin@example.test")

    pending = api._materialize_relative_schedule(testing)
    materialized = api._materialize_relative_schedule(active)

    assert pending.schedule == "in 30m"
    assert materialized.schedule != "in 30m"
    assert parse_schedule(str(materialized.schedule))["kind"] == "once"


def test_missing_legacy_relative_one_shot_is_disabled_not_recreated(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(
        update={"cron_job_id": "missing-cron", "schedule": "in 30m"}
    )
    store = _WorkflowStore(workflow)
    dashboard = SimpleNamespace(_list_cron_jobs_sync=lambda _profile: [])
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api, "_create_cron_job", lambda *_args: pytest.fail("Une échéance ambiguë ne doit pas être recréée."))

    api._reconcile_scheduled_workflows(store)

    assert store.workflow.status is CORE.WorkflowStatus.DISABLED


def test_reconciliation_disables_completed_one_shot_without_resuming(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(
        update={"cron_job_id": "linked-cron", "schedule": "2026-10-03T10:00:00+00:00"}
    )
    store = _WorkflowStore(workflow)
    dashboard = SimpleNamespace(
        _list_cron_jobs_sync=lambda _profile: [{
            "id": "linked-cron",
            "name": f"{api.MANAGED_CRON_PREFIX}{workflow.id}:Rapport",
            "schedule_display": workflow.schedule,
            "enabled": False,
            "state": "completed",
        }],
        _resume_cron_job_sync=lambda *_args: pytest.fail("Une tâche ponctuelle terminée ne doit pas reprendre."),
    )
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)

    api._reconcile_scheduled_workflows(store)
    api._reconcile_scheduled_workflows(store)

    assert store.workflow.status is CORE.WorkflowStatus.DISABLED


def test_reconciliation_does_not_recreate_expired_missing_one_shot(monkeypatch: pytest.MonkeyPatch) -> None:
    api = _load_frugal_api()
    workflow = _scheduled_workflow(CORE.WorkflowStatus.ACTIVE).model_copy(
        update={"cron_job_id": "missing-cron", "schedule": "2020-01-01T10:00:00+00:00"}
    )
    store = _WorkflowStore(workflow)
    dashboard = SimpleNamespace(_list_cron_jobs_sync=lambda _profile: [])
    monkeypatch.setattr(api, "_cron_dashboard", lambda: dashboard)
    monkeypatch.setattr(api, "_create_cron_job", lambda *_args: pytest.fail("Une tâche expirée ne doit pas être recréée."))

    api._reconcile_scheduled_workflows(store)

    assert store.workflow.status is CORE.WorkflowStatus.DISABLED


def test_router_lifespan_reconciles_at_application_start(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    api = _load_frugal_api()
    store = _WorkflowStore(_scheduled_workflow(CORE.WorkflowStatus.TESTING))
    observed: list[object] = []
    app = FastAPI()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(api, "_runtime", lambda: SimpleNamespace(automations=store))
    monkeypatch.setattr(api, "_reconcile_scheduled_workflows", lambda value: observed.append(value))
    app.include_router(api.router)

    with TestClient(app):
        pass

    assert observed == [store]
