"""Persistance atomique et sauvegardable des définitions d’agents."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import AgentContractError
from .models import AgentDefinition, AgentHarness


LEGACY_DIRECTIVE_FILES = ("AGENTS.md", "RULES.md", "SECURITY.md", "TOOLS.md")
HARNESS_MIGRATION_KEY = "harness_migration"
HARNESS_MIGRATION_VALUE = "global-v1"
LEGACY_TRUNCATION_MARKER = "\n\n[Contenu historique complet conservé dans le fichier source.]"


class AgentRepository:
    def __init__(self, path: Path, defaults: tuple[AgentDefinition, ...]) -> None:
        self._path = path
        self._defaults = defaults

    def load(self) -> tuple[AgentDefinition, ...]:
        if not self._path.is_file():
            return self._defaults
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            return tuple(
                AgentDefinition.model_validate_json(json.dumps(item))
                for item in payload["agents"]
            )
        except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise AgentContractError("Le registre des agents est invalide.") from exc

    def save(self, agents: tuple[AgentDefinition, ...]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        content = json.dumps({"version": 1, "agents": [item.model_dump(mode="json") for item in agents]}, ensure_ascii=False, indent=2)
        descriptor, name = tempfile.mkstemp(prefix=".agents.", dir=self._path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content + "\n")
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise AgentContractError("Le registre des agents ne peut pas être enregistré.") from exc


def migrate_legacy_harness(
    repository: AgentRepository, legacy_root: Path
) -> tuple[AgentDefinition, ...]:
    agents = repository.load()
    arc = next((agent for agent in agents if agent.id == "arc"), None)
    if arc is None or arc.metadata.get(HARNESS_MIGRATION_KEY):
        return agents
    harness = _legacy_harness(legacy_root) or arc.harness
    migrated = tuple(_migrated_agent(agent, harness) for agent in agents)
    repository.save(migrated)
    return migrated


def _legacy_harness(legacy_root: Path) -> AgentHarness | None:
    context = _bounded_legacy(_read_optional(legacy_root / "CONTEXT.md"), 16_000)
    memory = _bounded_legacy(_read_optional(legacy_root / "MEMORY.md"), 32_000)
    directives = _bounded_legacy(_legacy_directives(legacy_root), 16_000)
    if not context and not directives and not memory:
        return None
    return AgentHarness(context=context, directives=directives, memory=memory)


def _legacy_directives(legacy_root: Path) -> str:
    sections = tuple(
        f"## {name}\n\n{content}"
        for name in LEGACY_DIRECTIVE_FILES
        if (content := _read_optional(legacy_root / name))
    )
    return "\n\n".join(sections)


def _read_optional(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise AgentContractError(f"Le paramètre historique {path.name} est illisible.") from exc


def _bounded_legacy(content: str, limit: int) -> str:
    if len(content) <= limit:
        return content
    available = limit - len(LEGACY_TRUNCATION_MARKER)
    return f"{content[:available].rstrip()}{LEGACY_TRUNCATION_MARKER}"


def _migrated_agent(agent: AgentDefinition, harness: AgentHarness) -> AgentDefinition:
    if agent.id != "arc":
        return agent
    metadata = {**agent.metadata, HARNESS_MIGRATION_KEY: HARNESS_MIGRATION_VALUE}
    return agent.model_copy(update={"harness": harness, "metadata": metadata})
