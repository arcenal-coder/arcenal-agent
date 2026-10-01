"""Validation du chargement complet du contrat de prompt ARC."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

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


def _managed_file(file_id: str) -> dict[str, object]:
    return {
        "content": f"{file_id}: " + ("directive contrôlée\n" * 300),
        "file": {"filename": f"{file_id.upper()}.md"},
    }


def test_arc_prompt_sections_fit_the_real_hermes_budget(monkeypatch) -> None:
    plugin = _load_plugin()
    supervisor = SimpleNamespace(
        managed_files=SimpleNamespace(read_managed_file=_managed_file)
    )
    monkeypatch.setattr(sys.modules[plugin.__name__ + ".tools"], "_supervisor_module", lambda: supervisor)
    manager = PluginManager()
    context = PluginContext(
        PluginManifest(name="ARCenal Supervisor", key="arcenal-supervisor", source="builtin"),
        manager,
    )

    plugin.register(context)
    rendered = manager.render_system_prompt_sections({"session_id": "preproduction"})
    sections = {section.id: section.content for section in rendered}

    assert set(sections) == {"arcenal.directives", "arcenal.identity", "arcenal.memory"}
    assert sections["arcenal.identity"] == plugin.ARC_SYSTEM_PROMPT.strip()
    for filename in ("AGENTS.md", "RULES.md", "SECURITY.md", "TOOLS.md"):
        assert filename in sections["arcenal.directives"]
    assert "[Suite disponible via arcenal_context_search]" in sections["arcenal.directives"]
    assert "[Suite disponible via arcenal_memory_search]" in sections["arcenal.memory"]


def test_bounded_excerpt_keeps_short_content_unchanged() -> None:
    plugin = _load_plugin()

    assert plugin._bounded_excerpt("  contenu utile  ", 40, "[suite]") == "contenu utile"


def test_bounded_excerpt_rejects_an_impossible_budget() -> None:
    plugin = _load_plugin()

    with pytest.raises(plugin.PromptBudgetError, match="trop petit"):
        plugin._bounded_excerpt("contenu", 4, "[suite]")
