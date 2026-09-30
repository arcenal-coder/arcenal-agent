"""Persistance atomique et sauvegardable des définitions d’agents."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import AgentContractError
from .models import AgentDefinition


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
