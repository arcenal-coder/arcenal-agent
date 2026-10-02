"""Validation du chargement complet du contrat de prompt ARC."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from hermes_cli.plugins import PluginContext, PluginManager, PluginManifest


PLUGIN_DIR = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor"


def _load_plugin() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "arcenal_supervisor_prompt_test",
        PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert spec and spec.loader
    plugin = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = plugin
    spec.loader.exec_module(plugin)
    return plugin


def test_arc_prompt_contains_only_the_active_agent_harness(monkeypatch, tmp_path: Path) -> None:
    plugin = _load_plugin()
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    manager = PluginManager()
    context = PluginContext(
        PluginManifest(name="ARCenal Supervisor", key="arcenal-supervisor", source="builtin"),
        manager,
    )

    plugin.register(context)
    rendered = manager.render_system_prompt_sections({"profile_name": "default", "session_id": "preproduction"})
    sections = {section.id: section.content for section in rendered}

    assert set(sections) == {"arcenal.harness"}
    assert "architecte et superviseur" in sections["arcenal.harness"]
    assert "# Contexte propre à l’agent" in sections["arcenal.harness"]
    assert "AGENTS.md" not in sections["arcenal.harness"]


def test_specialized_profile_uses_its_own_markdown_parameters(monkeypatch, tmp_path: Path) -> None:
    plugin = _load_plugin()
    root = tmp_path / "profiles" / "veille"
    (root / "memories").mkdir(parents=True)
    (root / "CONTEXT.md").write_text("Contexte veille", encoding="utf-8")
    (root / "DIRECTIVES.md").write_text("Directive veille", encoding="utf-8")
    (root / "memories" / "MEMORY.md").write_text("Mémoire veille", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    rendered = plugin._agent_harness_prompt({"profile_name": "veille"})

    assert "Contexte veille" in rendered
    assert "Directive veille" in rendered
    assert "Mémoire veille" in rendered


def test_active_profile_home_is_used_directly(monkeypatch, tmp_path: Path) -> None:
    plugin = _load_plugin()
    root = tmp_path / "veille"
    root.mkdir()
    (root / "CONTEXT.md").write_text("Contexte du processus actif", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(root))

    rendered = plugin._agent_harness_prompt({"profile_name": "veille"})

    assert "Contexte du processus actif" in rendered


def test_bounded_excerpt_keeps_short_content_unchanged() -> None:
    plugin = _load_plugin()

    assert plugin._bounded_excerpt("  contenu utile  ", 40, "[suite]") == "contenu utile"


def test_bounded_excerpt_rejects_an_impossible_budget() -> None:
    plugin = _load_plugin()

    with pytest.raises(plugin.PromptBudgetError, match="trop petit"):
        plugin._bounded_excerpt("contenu", 4, "[suite]")
