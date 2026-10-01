"""Classification locale et explicable des demandes ARC."""

from __future__ import annotations

import re

from .frugal_models import CapabilityProfile, TaskType


PATTERNS: tuple[tuple[TaskType, re.Pattern[str]], ...] = (
    (TaskType.DETERMINISTIC, re.compile(r"\b(calcul|combien font|statut|état du service|version)\b", re.I)),
    (TaskType.RETRIEVAL, re.compile(r"\b(cherche|retrouve|document|procédure|lda|wiki|mémoire)\b", re.I)),
    (TaskType.CLASSIFICATION, re.compile(r"\b(classe|catégorise|catégorie)\b", re.I)),
    (TaskType.EXTRACTION, re.compile(r"\b(extrais|extrait|champs|entités)\b", re.I)),
    (TaskType.TRANSFORMATION, re.compile(r"\b(traduis|reformule|convertis|résume)\b", re.I)),
    (TaskType.GENERATION, re.compile(r"\b(rédige|écris|génère|prépare)\b", re.I)),
    (TaskType.REASONING, re.compile(r"\b(analyse|compare|diagnostique|pourquoi|stratégie)\b", re.I)),
    (TaskType.TOOL_EXECUTION, re.compile(r"\b(installe|redémarre|répare|exécute|configure)\b", re.I)),
    (TaskType.WORKFLOW, re.compile(r"\b(workflow|processus|routine|automatisation)\b", re.I)),
)


def classify_task(message: str) -> TaskType:
    normalized = " ".join(message.split())
    match = next((kind for kind, pattern in PATTERNS if pattern.search(normalized)), None)
    return match or TaskType.UNKNOWN


def required_capability(task_type: TaskType, message: str) -> CapabilityProfile:
    if task_type is TaskType.DETERMINISTIC:
        return CapabilityProfile.DETERMINISTIC
    if task_type in {TaskType.CLASSIFICATION, TaskType.EXTRACTION, TaskType.TRANSFORMATION}:
        return CapabilityProfile.LIGHT
    if task_type in {TaskType.REASONING, TaskType.TOOL_EXECUTION} or len(message) > 4_000:
        return CapabilityProfile.ADVANCED
    return CapabilityProfile.STANDARD
