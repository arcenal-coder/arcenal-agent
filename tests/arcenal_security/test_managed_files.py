from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import Mock, patch

from fastapi import HTTPException


def _load_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "managed_files_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_managed_files_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Le module des fichiers administrés est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def _request(headers: dict[str, str]) -> Mock:
    request = Mock()
    request.headers = headers
    return request


class ManagedFilesTests(TestCase):
    def test_actor_uses_authenticated_yunohost_identity(self) -> None:
        self.assertEqual(MODULE._actor(_request({"x-remote-user": "admin@example.test"})), "admin@example.test")

    def test_actor_rejects_control_characters_and_has_a_fallback(self) -> None:
        self.assertEqual(MODULE._actor(_request({"x-remote-user": "admin\nforged"})), "adminforged")
        self.assertEqual(MODULE._actor(_request({})), "administrateur")

    def test_write_archives_then_persists_content_and_metadata(self) -> None:
        target = Path("/private/CONTEXT.md")
        metadata = Path("/private/.context.metadata.json")
        with (
            patch.object(MODULE, "_validate_content") as validate,
            patch.object(MODULE, "_archive_current") as archive,
            patch.object(MODULE, "_target", return_value=target),
            patch.object(MODULE, "_metadata_path", return_value=metadata),
            patch.object(MODULE, "_atomic_write") as write,
            patch.object(MODULE, "_write_json") as write_json,
            patch.object(MODULE, "read_managed_file", return_value={"content": "# Contexte"}),
        ):
            result = MODULE.write_managed_file("context", "# Contexte", "admin")
        validate.assert_called_once_with("# Contexte")
        archive.assert_called_once_with("context")
        write.assert_called_once_with(target, "# Contexte")
        self.assertEqual(write_json.call_args.args[1]["author"], "admin")
        self.assertEqual(result, {"content": "# Contexte"})

    def test_restore_refuses_an_invalid_version_identifier(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE.restore_managed_file("context", "../../secret", "admin")
        self.assertEqual(raised.exception.status_code, 422)

    def test_history_refuses_an_unknown_identifier_before_accessing_storage(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE._history_root("..")
        self.assertEqual(raised.exception.status_code, 404)

    def test_content_rejects_null_bytes(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            MODULE._validate_content("texte\x00invalide")
        self.assertEqual(raised.exception.status_code, 422)

    def test_read_json_reports_corrupted_metadata(self) -> None:
        metadata = Mock(spec=Path)
        metadata.is_file.return_value = True
        metadata.read_text.return_value = "{invalide"
        with self.assertRaises(HTTPException) as raised:
            MODULE._read_json(metadata)
        self.assertEqual(raised.exception.status_code, 500)
