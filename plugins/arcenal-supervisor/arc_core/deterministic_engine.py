"""Règles déterministes versionnées et auditables d'ARC Frugal."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Callable

from .models import EffectiveContext, EngineOutput


Handler = Callable[[EffectiveContext, str], EngineOutput | None]


@dataclass(frozen=True, slots=True)
class DeterministicRule:
    id: str
    version: int
    provenance: str
    enabled: bool
    handler: Handler


class DeterministicEngine:
    def __init__(self, rules: tuple[DeterministicRule, ...] | None = None) -> None:
        self._rules = rules or default_rules()

    def execute(self, context: EffectiveContext, message: str) -> EngineOutput | None:
        for rule in self._rules:
            output = rule.handler(context, message) if rule.enabled else None
            if output is not None:
                usage = {**output.usage, "rule_id": rule.id, "rule_version": rule.version, "rule_provenance": rule.provenance}
                return output.model_copy(update={"usage": usage})
        return None


def _structured_status(context: EffectiveContext, message: str) -> EngineOutput | None:
    if not re.search(r"\b(statut|état)\b", message, re.I):
        return None
    status = context.request_context.get("status")
    return EngineOutput(response=f"Statut : {status}") if status else None


def _calculation(_context: EffectiveContext, message: str) -> EngineOutput | None:
    match = re.search(r"(?:calcul|combien font)\s*[:：]?\s*([0-9+\-*/(). ]+)", message, re.I)
    if match is None:
        return None
    try:
        value = _evaluate(ast.parse(match.group(1), mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError):
        return None
    return EngineOutput(response=f"Résultat : {value:g}")


def _evaluate(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        factor = 1 if isinstance(node.op, ast.UAdd) else -1
        return factor * _evaluate(node.operand)
    if not isinstance(node, ast.BinOp):
        raise ValueError("Expression arithmétique non autorisée.")
    left, right = _evaluate(node.left), _evaluate(node.right)
    if isinstance(node.op, ast.Add):
        return left + right
    if isinstance(node.op, ast.Sub):
        return left - right
    if isinstance(node.op, ast.Mult):
        return left * right
    if isinstance(node.op, ast.Div):
        return left / right
    raise ValueError("Opérateur arithmétique non autorisé.")


def default_rules() -> tuple[DeterministicRule, ...]:
    return (
        DeterministicRule("structured-status", 1, "ARC Core", True, _structured_status),
        DeterministicRule("safe-calculation", 1, "ARC Core", True, _calculation),
    )
