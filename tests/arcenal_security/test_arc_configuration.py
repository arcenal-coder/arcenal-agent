from __future__ import annotations

import importlib.util
import os
import sys
import json
from pathlib import Path
from types import ModuleType

import pytest


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


def _legacy_config() -> dict[str, object]:
    return {
        "model": {"provider": "openrouter", "default": "openrouter/auto"},
        "providers": {"openrouter": {"enabled": True}},
        "arcenal": {"access_credentials": [{"id": "ats", "secretEnv": "ARCENAL_ACCESS_ATS_API_KEY"}]},
    }


def test_native_config_preserves_typed_namespaces(tmp_path: Path) -> None:
    store = CORE.ArcNativeConfigStore(tmp_path / "arcenal" / "config.json")

    store.set("ui", "dark", True)
    store.set("system", "retries", 3)
    store.set("providers", "openrouter", {"enabled": True, "weight": 0.5})

    assert store.get("ui", "dark") is True
    assert store.get("system", "retries") == 3
    assert store.list("providers") == {"openrouter": {"enabled": True, "weight": 0.5}}
    assert store.exists("ui", "dark") is True
    store.delete("ui", "dark")
    assert store.exists("ui", "dark") is False
    assert (tmp_path / "arcenal").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "arcenal" / "config.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("namespace,key", [("../system", "mode"), ("core", "bad key"), ("", "mode")])
def test_native_config_rejects_unsafe_keys(tmp_path: Path, namespace: str, key: str) -> None:
    store = CORE.ArcNativeConfigStore(tmp_path / "config.json")

    with pytest.raises(CORE.ArcConfigurationKeyError):
        store.set(namespace, key, "value")


def test_native_config_rejects_non_json_values(tmp_path: Path) -> None:
    store = CORE.ArcNativeConfigStore(tmp_path / "config.json")

    with pytest.raises(CORE.ArcConfigurationValueError):
        store.set("core", "invalid", {"value": object()})
    with pytest.raises(CORE.ArcConfigurationValueError):
        store.set("core", "invalid_float", float("nan"))


def test_native_config_rejects_a_corrupted_document(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(CORE.ArcConfigurationError, match="illisible"):
        CORE.ArcNativeConfigStore(path).list("core")


def test_vault_rotates_deletes_and_protects_secrets(tmp_path: Path) -> None:
    vault = CORE.ArcFileVault(tmp_path / ".env")

    vault.set_secret("OPENROUTER_API_KEY", "ancien-secret")
    vault.set_secret("OPENROUTER_API_KEY", "nouveau-secret")

    assert vault.get_secret("OPENROUTER_API_KEY") == "nouveau-secret"
    assert "ancien-secret" not in (tmp_path / ".env").read_text(encoding="utf-8")
    assert vault.has_secret("OPENROUTER_API_KEY") is True
    assert (tmp_path / ".env").stat().st_mode & 0o777 == 0o600
    vault.delete_secret("OPENROUTER_API_KEY")
    assert vault.has_secret("OPENROUTER_API_KEY") is False
    with pytest.raises(CORE.ArcSecretMissingError, match="OPENROUTER_API_KEY"):
        vault.require_secret("OPENROUTER_API_KEY")


def test_runtime_secret_has_priority_without_being_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    vault = CORE.ArcFileVault(tmp_path / ".env")
    vault.set_secret("OPENAI_API_KEY", "persistant")
    monkeypatch.setenv("OPENAI_API_KEY", "runtime")

    assert vault.get_secret("OPENAI_API_KEY") == "runtime"
    assert "runtime" not in (tmp_path / ".env").read_text(encoding="utf-8")


def test_vault_rejects_invalid_or_empty_secrets(tmp_path: Path) -> None:
    vault = CORE.ArcFileVault(tmp_path / ".env")

    with pytest.raises(CORE.ArcSecretKeyError):
        vault.set_secret("bad-key", "secret")
    with pytest.raises(CORE.ArcSecretKeyError):
        vault.set_secret("LD_PRELOAD", "secret")
    with pytest.raises(CORE.ArcSecretValueError):
        vault.set_secret("VALID_KEY", "")
    with pytest.raises(CORE.ArcSecretValueError):
        vault.set_secret("VALID_KEY", "   ")


def test_vault_treats_a_legacy_empty_value_as_missing(tmp_path: Path) -> None:
    path = tmp_path / ".env"
    path.write_text('OPENROUTER_API_KEY=""\n', encoding="utf-8")

    assert CORE.ArcFileVault(path).has_secret("OPENROUTER_API_KEY") is False


def test_vault_preserves_special_characters(tmp_path: Path) -> None:
    vault = CORE.ArcFileVault(tmp_path / ".env")
    secret = "ligne 1\nligne=2#valeur\\fin"

    vault.set_secret("SPECIAL_KEY", secret)

    assert vault.get_secret("SPECIAL_KEY") == secret


def test_hermes_adapter_and_native_store_produce_equivalent_values(tmp_path: Path) -> None:
    legacy = CORE.HermesConfigAdapter(_legacy_config)
    native = CORE.ArcNativeConfigStore(tmp_path / "config.json")
    report = CORE.migrate_hermes_configuration(native, legacy)

    assert native.get("models", "provider") == legacy.get("models", "provider")
    assert native.get("providers", "openrouter") == legacy.get("providers", "openrouter")
    assert report.copied == 4
    with pytest.raises(CORE.ArcConfigurationReadOnlyError):
        legacy.set("models", "provider", "openai")


def test_migration_is_idempotent_and_reports_conflicts(tmp_path: Path) -> None:
    legacy = CORE.HermesConfigAdapter(_legacy_config)
    native = CORE.ArcNativeConfigStore(tmp_path / "config.json")

    first = CORE.migrate_hermes_configuration(native, legacy)
    second = CORE.migrate_hermes_configuration(native, legacy)
    native.set("models", "provider", "ollama")
    conflict = CORE.migrate_hermes_configuration(native, legacy)

    assert first.copied == 4
    assert second.copied == 0
    assert second.unchanged == 4
    assert conflict.conflicts == ("models.provider",)
    assert native.get("models", "provider") == "ollama"


def test_migration_accepts_an_empty_legacy_configuration(tmp_path: Path) -> None:
    native = CORE.ArcNativeConfigStore(tmp_path / "config.json")

    report = CORE.migrate_hermes_configuration(native, CORE.HermesConfigAdapter(lambda: {}))

    assert report.copied == 0
    assert report.unchanged == 0
    assert report.conflicts == ()


def test_migration_preserves_legacy_auxiliary_models(tmp_path: Path) -> None:
    legacy = CORE.HermesConfigAdapter(lambda: {"auxiliary": {"vision": {"provider": "gemini", "model": "flash"}}})
    native = CORE.ArcNativeConfigStore(tmp_path / "config.json")

    CORE.migrate_hermes_configuration(native, legacy)

    assert native.get("models", "auxiliary") == {"vision": {"provider": "gemini", "model": "flash"}}


def test_runtime_exposes_migration_conflicts(tmp_path: Path) -> None:
    native = CORE.ArcNativeConfigStore(tmp_path / "config.json")
    native.set("models", "provider", "ollama")
    report = CORE.migrate_hermes_configuration(native, CORE.HermesConfigAdapter(_legacy_config))

    runtime = CORE.ArcRuntimeConfiguration(native, CORE.ArcFileVault(tmp_path / ".env"), report)

    assert runtime.migration.conflicts == ("models.provider",)


def test_runtime_rejects_an_unknown_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARCENAL_CONFIG_BACKEND", "inconnu")

    with pytest.raises(CORE.ArcConfigurationError, match="Backend"):
        CORE.runtime_configuration()


def test_provider_resolution_uses_arc_config_and_vault(tmp_path: Path) -> None:
    config = CORE.ArcNativeConfigStore(tmp_path / "config.json")
    vault = CORE.ArcFileVault(tmp_path / ".env")
    config.set("models", "provider", "openrouter")
    config.set("models", "default", "openrouter/auto")
    config.set("providers", "openrouter", {"enabled": True})
    vault.set_secret("OPENROUTER_API_KEY", "secret")
    runtime = CORE.ArcRuntimeConfiguration(config, vault)

    assert runtime.provider_enabled("openrouter", "OPENROUTER_API_KEY") is True
    assert runtime.model_selection() == ("openrouter", "openrouter/auto")
    vault.delete_secret("OPENROUTER_API_KEY")
    assert runtime.provider_enabled("openrouter", "OPENROUTER_API_KEY") is False


def test_arc_has_only_one_direct_hermes_config_import() -> None:
    root = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor"
    offenders = []
    for path in root.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        if "from hermes_cli.config" in content or "import hermes_cli.config" in content:
            offenders.append(path.relative_to(root).as_posix())

    assert offenders == ["arc_core/hermes_config_adapter.py"]


def test_arc_is_the_default_backend_without_environment_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARCENAL_CONFIG_BACKEND", raising=False)

    runtime = CORE.runtime_configuration(tmp_path)

    assert runtime.backend == "arc"
    assert runtime.migration_state == "not_required"
    assert runtime.config.exists("system", "hermes_migration") is True


def test_native_startup_does_not_initialize_hermes_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules["arcenal_arc_core.configuration_runtime"]
    monkeypatch.delenv("ARCENAL_CONFIG_BACKEND", raising=False)
    monkeypatch.setattr(module, "HermesConfigAdapter", lambda: pytest.fail("Hermes Config ne doit pas démarrer"))

    assert CORE.runtime_configuration(tmp_path).backend == "arc"


def test_explicit_legacy_backend_remains_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules["arcenal_arc_core.configuration_runtime"]
    monkeypatch.setenv("ARCENAL_CONFIG_BACKEND", "hermes")
    monkeypatch.setattr(module, "HermesConfigAdapter", lambda: CORE.HermesConfigAdapter(_legacy_config))

    runtime = CORE.runtime_configuration(tmp_path)

    assert runtime.backend == "hermes"
    assert runtime.migration_state == "legacy"
    with pytest.raises(CORE.ArcConfigurationReadOnlyError):
        runtime.config.set("models", "provider", "openai")


def test_existing_install_migrates_once_and_preserves_arc_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    module = sys.modules["arcenal_arc_core.configuration_runtime"]
    (tmp_path / "config.yaml").write_text("legacy: true\n", encoding="utf-8")
    native = CORE.ArcNativeConfigStore(tmp_path / "arcenal" / "config.json")
    native.set("models", "provider", "ollama")
    monkeypatch.delenv("ARCENAL_CONFIG_BACKEND", raising=False)
    monkeypatch.setattr(module, "HermesConfigAdapter", lambda: CORE.HermesConfigAdapter(_legacy_config))

    states = [CORE.runtime_configuration(tmp_path) for _iteration in range(3)]

    assert all(runtime.backend == "arc" for runtime in states)
    assert all(runtime.config.get("models", "provider") == "ollama" for runtime in states)
    assert states[0].migration.conflicts == ("models.provider",)
    assert states[1].migration == states[0].migration == states[2].migration
    assert "models.provider" in caplog.text


def test_native_error_never_falls_back_to_hermes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules["arcenal_arc_core.configuration_runtime"]
    target = tmp_path / "arcenal"
    target.mkdir()
    (target / "config.json").write_text("{broken", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("legacy: true\n", encoding="utf-8")
    monkeypatch.delenv("ARCENAL_CONFIG_BACKEND", raising=False)
    monkeypatch.setattr(module, "HermesConfigAdapter", lambda: pytest.fail("Fallback Hermes interdit"))

    with pytest.raises(CORE.ArcConfigurationError, match="illisible"):
        CORE.runtime_configuration(tmp_path)


def test_migration_marker_contains_no_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules["arcenal_arc_core.configuration_runtime"]
    (tmp_path / "config.yaml").write_text("legacy: true\n", encoding="utf-8")
    monkeypatch.setattr(module, "HermesConfigAdapter", lambda: CORE.HermesConfigAdapter(_legacy_config))

    CORE.runtime_configuration(tmp_path)

    document = json.loads((tmp_path / "arcenal" / "config.json").read_text(encoding="utf-8"))
    marker = document["system"]["hermes_migration"]
    assert "secret" not in json.dumps(marker).casefold()
