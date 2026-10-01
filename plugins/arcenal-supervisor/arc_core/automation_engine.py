"""Workflows déterministes et observation gouvernée des processus."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .errors import AutomationPolicyError
from .frugal_models import AutomationCandidate, AutomationWorkflow, ProcessObservation, WorkflowStatus
from .frugal_store import JsonCollectionStore
from .models import EffectiveContext, EngineOutput


class AutomationStore:
    def __init__(self, root: Path) -> None:
        self._workflows = JsonCollectionStore(root / "workflows.json", AutomationWorkflow, "workflows")
        self._candidates = JsonCollectionStore(root / "automation-candidates.json", AutomationCandidate, "candidates")
        self._observations = JsonCollectionStore(root / "process-observations.json", ProcessObservation, "observations")

    def workflows(self) -> tuple[AutomationWorkflow, ...]:
        return self._workflows.load()

    def candidates(self) -> tuple[AutomationCandidate, ...]:
        return self._candidates.load()

    def observations(self) -> tuple[ProcessObservation, ...]:
        return self._observations.load()

    def save_workflow(self, workflow: AutomationWorkflow) -> AutomationWorkflow:
        values = tuple(item for item in self.workflows() if item.id != workflow.id)
        self._workflows.save((*values, workflow))
        return workflow

    def save_candidate(self, candidate: AutomationCandidate) -> AutomationCandidate:
        values = tuple(item for item in self.candidates() if item.id != candidate.id)
        self._candidates.save((*values, candidate))
        return candidate

    def save_observation(self, observation: ProcessObservation) -> None:
        self._observations.save((*self.observations(), observation))


class WorkflowEngine:
    def __init__(self, store: AutomationStore) -> None:
        self._store = store

    def execute(self, context: EffectiveContext, message: str) -> EngineOutput | None:
        workflow = next((item for item in self._store.workflows() if self._matches(item, context, message)), None)
        if workflow is None:
            return None
        self._validate_permissions(workflow, context)
        values = self._steps(workflow, context)
        if values is None:
            return None
        updated = workflow.model_copy(update={"executions": workflow.executions + 1, "updated_at": datetime.now(timezone.utc)})
        self._store.save_workflow(updated)
        return EngineOutput(response=values, usage={"workflow_id": workflow.id, "workflow_version": workflow.version})

    def _matches(self, workflow: AutomationWorkflow, context: EffectiveContext, message: str) -> bool:
        return workflow.status is WorkflowStatus.ACTIVE and workflow.agent_id == context.agent.id and workflow.approved_by is not None and workflow.trigger.casefold() in message.casefold()

    def _validate_permissions(self, workflow: AutomationWorkflow, context: EffectiveContext) -> None:
        if not set(workflow.permissions).issubset(context.permissions):
            raise AutomationPolicyError("Le workflow demande des permissions absentes du contrat de l'agent.")
        tools = {step.tool for step in workflow.steps if step.tool}
        if not tools.issubset(context.tools):
            raise AutomationPolicyError("Le workflow tente d'appeler un outil non autorisé.")

    def _steps(self, workflow: AutomationWorkflow, context: EffectiveContext) -> str | None:
        result = ""
        for step in workflow.steps:
            value = context.request_context.get(step.input_key or "") if step.operation == "structured_value" else None
            if step.operation == "structured_value" and value is None:
                return self._exception(workflow)
            result = value or (step.template or "").format(result=result)
        return result or None

    def _exception(self, workflow: AutomationWorkflow) -> None:
        updated = workflow.model_copy(update={"exceptions": workflow.exceptions + 1, "updated_at": datetime.now(timezone.utc)})
        self._store.save_workflow(updated)
        return None


class ProcessObserver:
    def __init__(self, store: AutomationStore, threshold: int = 3) -> None:
        self._store = store
        self._threshold = threshold

    def observe(self, context: EffectiveContext, tools: tuple[str, ...], outcome: str) -> AutomationCandidate | None:
        observation = self._observation(context, tools, outcome)
        self._store.save_observation(observation)
        similar = tuple(item for item in self._store.observations() if item.fingerprint == observation.fingerprint)
        if len(similar) < self._threshold:
            return None
        existing = next((item for item in self._store.candidates() if item.id == observation.fingerprint), None)
        candidate = self._candidate(observation, len(similar), existing)
        return self._store.save_candidate(candidate)

    def _observation(self, context: EffectiveContext, tools: tuple[str, ...], outcome: str) -> ProcessObservation:
        keys = tuple(sorted(context.request_context))
        fingerprint = hashlib.sha256("\0".join((context.agent.id, *tools, *keys)).encode()).hexdigest()[:24]
        signature = hashlib.sha256(outcome.encode()).hexdigest()[:24]
        return ProcessObservation(id=str(uuid4()), agent_id=context.agent.id, fingerprint=fingerprint, tools=tools, input_keys=keys, outcome_signature=signature, created_at=datetime.now(timezone.utc))

    def _candidate(self, observation: ProcessObservation, count: int, existing: AutomationCandidate | None) -> AutomationCandidate:
        confidence = min(0.99, count / (count + 1))
        return AutomationCandidate(id=observation.fingerprint, name=f"Processus observé {observation.agent_id}", description="Séquence répétitive détectée, à examiner avant tout test.", observations=count, steps=existing.steps if existing else (), inputs=observation.input_keys, outputs=("response",), exceptions=("Donnée structurée absente",), confidence=confidence, estimated_savings=0, risk_level="medium", reviewed=existing.reviewed if existing else False)


def transition_workflow(workflow: AutomationWorkflow, status: WorkflowStatus, actor: str) -> AutomationWorkflow:
    allowed = {
        WorkflowStatus.DRAFT: {WorkflowStatus.TESTING, WorkflowStatus.ARCHIVED},
        WorkflowStatus.TESTING: {WorkflowStatus.ACTIVE, WorkflowStatus.DISABLED, WorkflowStatus.ARCHIVED},
        WorkflowStatus.ACTIVE: {WorkflowStatus.DISABLED, WorkflowStatus.ARCHIVED},
        WorkflowStatus.DISABLED: {WorkflowStatus.TESTING, WorkflowStatus.ARCHIVED},
        WorkflowStatus.ARCHIVED: set(),
    }
    if status not in allowed[workflow.status]:
        raise AutomationPolicyError("Cette transition de workflow n'est pas autorisée.")
    approval = actor if status is WorkflowStatus.ACTIVE else workflow.approved_by
    return workflow.model_copy(update={"status": status, "approved_by": approval, "updated_at": datetime.now(timezone.utc)})
