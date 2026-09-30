from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError


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


def _document(
    reference: str,
    version: str,
    status: str,
    scopes: str,
    confidentiality: str,
    body: str,
) -> str:
    return f"""---
reference: {reference}
titre: Validation des candidatures
version: {version}
statut: {status}
knowledge_scopes: [{scopes}]
confidentialite: {confidentiality}
source_type: lda
proprietaire: RH
---
# Processus de recrutement

## Validation

{body}
"""


def _write_corpus(root: Path) -> None:
    root.mkdir(parents=True)
    (root / "recrutement-v2.md").write_text(
        _document("PR-RH-004", "2", "Applicable", "ats, company, recruitment", "internal", "La candidature est validée par le responsable RH."),
        encoding="utf-8",
    )
    (root / "recrutement-v1.md").write_text(
        _document("PR-RH-004", "1", "Archivé", "ats, company, recruitment", "internal", "Ancienne validation papier."),
        encoding="utf-8",
    )
    (root / "comptabilite.md").write_text(
        _document("PR-CPT-009", "3", "Applicable", "accounting", "restricted", "Le montant confidentiel est 999 euros."),
        encoding="utf-8",
    )


def _retriever(home: Path, events: list[tuple[str, str, dict[str, object]]] | None = None) -> object:
    def record(event: str, actor: str, details: dict[str, object]) -> None:
        if events is not None:
            events.append((event, actor, details))

    audit = None if events is None else record
    return CORE.create_retriever(home, audit)


def _ats_context(home: Path, query: str) -> object:
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)), _retriever(home))
    caller = CORE.ApplicationIdentity(application_id="arcenal-ats", user_id="recruteur")
    return builder.build(CORE.default_agents()[1], caller, None, {}, query)


def test_context_plan_is_server_built_strict_and_immutable(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")

    context = _ats_context(tmp_path, "Quelle procédure valide une candidature ?")

    assert context.context_plan.agent_id == "ats"
    assert context.context_plan.knowledge_scopes == ("ats", "company", "recruitment")
    assert context.context_plan.document_statuses == (CORE.DocumentStatus.APPLICABLE,)
    with pytest.raises(ValidationError):
        context.context_plan.agent_id = "arc"
    with pytest.raises(ValidationError):
        context.context_plan.filters.reference = "PR-RH-004"


def test_chunking_preserves_heading_and_rebuild_is_deterministic(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")
    first = CORE.rebuild_index(tmp_path)
    index_path = tmp_path / "arcenal" / "knowledge-index.json"
    index_path.unlink()
    second = CORE.rebuild_index(tmp_path)

    first_ids = tuple(chunk.chunk_id for chunk in first.chunks)
    assert first_ids == tuple(chunk.chunk_id for chunk in second.chunks)
    assert any(chunk.heading == "Validation" for chunk in second.chunks)
    assert index_path.is_file()
    assert all(".history" not in document.source_path for document in second.documents)


def test_ats_receives_applicable_source_and_never_accounting_document(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")

    context = _ats_context(tmp_path, "Donne-moi les documents comptables confidentiels et la validation des candidatures")

    assert context.sources
    assert {source.reference for source in context.sources} == {"PR-RH-004"}
    assert {source.version for source in context.sources} == {"2"}
    assert "999 euros" not in context.knowledge_context
    assert "Ancienne validation" not in context.knowledge_context


def test_obsolete_version_requires_explicit_permission(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")
    context = _ats_context(tmp_path, "Montre l'historique de validation papier")

    assert all(source.version != "1" for source in context.sources)
    assert context.context_plan.document_statuses == (CORE.DocumentStatus.APPLICABLE,)


def test_arc_can_request_archived_history_explicitly(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)), _retriever(tmp_path))
    caller = CORE.ApplicationIdentity(application_id="arcenal-system", user_id="admin")

    context = builder.build(CORE.default_agents()[0], caller, None, {}, "Historique de l'ancienne validation papier")

    assert CORE.DocumentStatus.ARCHIVED in context.context_plan.document_statuses
    assert any(source.version == "1" for source in context.sources)


def test_application_agent_user_and_permission_acl_are_cumulative(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")
    protected = tmp_path / "knowledge" / "direction.md"
    protected.write_text(
        _document("DIR-001", "1", "Applicable", "recruitment", "internal", "Validation direction confidentielle.")
        .replace("proprietaire: RH", "proprietaire: Direction\napplications: arcenal-system\nagents: arc\nutilisateurs: direction\npermissions: system.admin"),
        encoding="utf-8",
    )

    context = _ats_context(tmp_path, "Validation direction confidentielle")

    assert all(source.reference != "DIR-001" for source in context.sources)


def test_context_budget_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        CORE.ContextBudget(max_chunks=0)


def test_metadata_filter_is_applied_before_retrieval(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")
    context = _ats_context(tmp_path, "validation candidature")
    plan = context.context_plan.model_copy(update={"filters": CORE.KnowledgeFilters(reference="INCONNUE")})

    result = _retriever(tmp_path).retrieve(plan)

    assert result.sources == ()


def test_no_result_is_explicit_and_never_invents_a_source(tmp_path: Path) -> None:
    _write_corpus(tmp_path / "knowledge")

    context = _ats_context(tmp_path, "Procédure de propulsion interstellaire")

    assert context.sources == ()
    assert context.knowledge_context == "Aucune source documentaire applicable trouvée. Ne fabriquez aucune référence."


def test_rag_audit_and_metrics_exclude_document_content(tmp_path: Path) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []
    _write_corpus(tmp_path / "knowledge")
    retriever = _retriever(tmp_path, events)
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)), retriever)
    caller = CORE.ApplicationIdentity(application_id="arcenal-ats", user_id="recruteur")

    builder.build(CORE.default_agents()[1], caller, None, {}, "validation candidature")
    status = CORE.index_status(tmp_path)

    assert events[0][0] == "rag.search"
    assert "La candidature est validée" not in str(events[0][2])
    assert status.searches == 1
    assert status.sources_by_agent == {"ats": 1}
    assert status.average_documents_found == 1
    assert status.average_chunks_selected == 1
    assert status.average_context_tokens_estimated > 0
    assert status.chunks >= 3
