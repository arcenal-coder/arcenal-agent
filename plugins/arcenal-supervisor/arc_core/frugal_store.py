"""Persistance atomique commune aux registres d'ARC Frugal."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import ValidationError

from .contracts import StrictModel
from .errors import FrugalStorageError


Item = TypeVar("Item", bound=StrictModel)


class JsonCollectionStore(Generic[Item]):
    def __init__(self, path: Path, item_type: type[Item], key: str) -> None:
        self._path = path
        self._item_type = item_type
        self._key = key

    def load(self) -> tuple[Item, ...]:
        if not self._path.is_file():
            return ()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            values = payload[self._key]
            if not isinstance(values, list):
                raise TypeError("Le registre doit contenir une liste.")
            return tuple(self._item_type.model_validate_json(json.dumps(item)) for item in values)
        except (OSError, KeyError, TypeError, ValueError, ValidationError) as exc:
            raise FrugalStorageError(f"Le registre {self._key} est invalide.") from exc

    def save(self, items: tuple[Item, ...]) -> None:
        content = self._serialize(items)
        temporary = self._temporary()
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, self._path)
            self._path.chmod(0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise FrugalStorageError(f"Le registre {self._key} est indisponible.") from exc

    def _serialize(self, items: tuple[Item, ...]) -> str:
        values = [item.model_dump(mode="json") for item in items]
        return json.dumps({"version": 1, self._key: values}, ensure_ascii=False, indent=2) + "\n"

    def _temporary(self) -> Path:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, name = tempfile.mkstemp(prefix=f".{self._key}.", dir=self._path.parent)
        os.close(descriptor)
        return Path(name)
