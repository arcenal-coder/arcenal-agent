from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError


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


def _draft(
    *, memory_type: str = "decision", scopes: tuple[str, ...] = ("company",),
    confidentiality: str = "internal", content: str = "SilverBullet est retenu.",
    expires_at: datetime | None = None,
) -> BaseModel:
    return CORE.MemoryDraft(
        memory_type=CORE.MemoryType(memory_type), summary="Choix de SilverBullet", content=content,
        provenance=CORE.MemoryProvenance(source_type=CORE.MemorySourceType.MANUAL, source_id="conseil-2026-09-30", recorded_at=datetime.now(timezone.utc), author="Direction"),
        retention_mode=CORE.RetentionMode.EXPIRING if expires_at else CORE.RetentionMode.PERMANENT,
        expires_at=expires_at, knowledge_scopes=scopes,
        confidentiality=CORE.ConfidentialityLevel(confidentiality), required_permissions=("memory.read",),
        project="ARCenal", relations=(CORE.MemoryRelation(relation_type="concerns", target_kind="project", target_id="arcenal"),),
    )


def _repository(tmp_path: Path):
    return CORE.EnterpriseMemoryRepository(CORE.memory_database_path(tmp_path))


def _context(home: Path, agent: object, application: str, query: str):
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)), CORE.create_retriever(home))
    caller = CORE.ApplicationIdentity(application_id=application, user_id="test")
    return builder.build(agent, caller, None, {}, query)


def test_memory_creation_correction_and_history(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    created = repository.create(_draft(), "admin")
    corrected = repository.correct(created.id, _draft(content="SilverBullet est retenu comme wiki léger."), "admin", "Précision")

    assert corrected.version == 2
    assert corrected.provenance.source_id == "conseil-2026-09-30"
    assert repository.history(created.id)[0].previous.content == "SilverBullet est retenu."
    assert repository.metrics().by_type == {"decision": 1}


def test_memory_correction_replaces_derived_index_content(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    created = repository.create(_draft(content="Le wiki retenu est provisoire."), "admin")
    CORE.rebuild_index(tmp_path)
    corrected = _draft(content="SilverBullet devient le wiki d’entreprise validé.")
    repository.correct(created.id, corrected, "admin", "Décision confirmée")
    CORE.rebuild_index(tmp_path)

    context = _context(tmp_path, CORE.default_agents()[0], "arcenal-system", "Quel est le wiki d’entreprise validé ?")

    assert "SilverBullet devient" in context.memory_context
    assert "wiki retenu est provisoire" not in context.memory_context


def test_memory_projection_preserves_governance_review_date(tmp_path: Path) -> None:
    review_date = datetime(2027, 3, 1, tzinfo=timezone.utc)
    draft = _draft().model_copy(update={"review_date": review_date})
    repository = _repository(tmp_path)
    repository.create(draft, "admin")

    loaded, errors = CORE.EnterpriseMemoryKnowledgeSource(repository).load()

    assert errors == ()
    assert loaded[0][0].review_date == "2027-03-01"


def test_memory_contract_rejects_missing_expiration_and_rule_authority() -> None:
    with pytest.raises(ValidationError, match="date d’expiration"):
        CORE.MemoryDraft.model_validate({**_draft().model_dump(), "retention_mode": CORE.RetentionMode.EXPIRING, "expires_at": None})
    with pytest.raises(ValidationError, match="document officiel"):
        CORE.MemoryDraft.model_validate({**_draft().model_dump(), "memory_type": CORE.MemoryType.RULE, "rule_kind": CORE.RuleKind.OFFICIAL_REFERENCE, "official_reference": None})


def test_expired_archived_and_deleted_memories_leave_active_store(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    expired = repository.create(_draft(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)), "admin")
    archived = repository.create(_draft(content="Décision archivable."), "admin")
    repository.set_status(archived.id, CORE.MemoryStatus.ARCHIVED, "admin", "Fin du projet")
    deleted = repository.create(_draft(content="Information à oublier."), "admin")
    repository.delete_physical(deleted.id)

    assert repository.active() == ()
    assert repository.get(expired.id).status is CORE.MemoryStatus.EXPIRED
    assert repository.get(archived.id).status is CORE.MemoryStatus.ARCHIVED
    with pytest.raises(CORE.MemoryNotFoundError):
        repository.get(deleted.id)


def test_logical_delete_stays_auditable_but_leaves_rag(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    memory = repository.create(_draft(), "admin")
    deleted = repository.set_status(memory.id, CORE.MemoryStatus.DELETED, "admin", "Information obsolète")
    CORE.rebuild_index(tmp_path)
    context = _context(tmp_path, CORE.default_agents()[0], "arcenal-system", "Pourquoi SilverBullet ?")

    assert deleted.status is CORE.MemoryStatus.DELETED
    assert repository.active() == ()
    assert repository.history(memory.id)[0].reason == "Information obsolète"
    assert context.sources == ()


def test_rag_separates_memory_and_prioritizes_official_knowledge(tmp_path: Path) -> None:
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "conges.md").write_text("""---
reference: PR-RH-010
titre: Validation des congés
statut: Applicable
source_type: lda
knowledge_scopes: [company]
---
# Congés

Les congés doivent être validés par écrit.
""", encoding="utf-8")
    _repository(tmp_path).create(_draft(content="Les congés peuvent être validés oralement."), "admin")

    context = _context(tmp_path, CORE.default_agents()[0], "arcenal-system", "Comment les congés sont-ils validés ?")

    assert context.sources[0].authority == "official"
    assert any(source.source_type is CORE.SourceType.ENTERPRISE_MEMORY for source in context.sources)
    assert context.knowledge_context.index("Official Knowledge") < context.knowledge_context.index("Enterprise Memory")
    assert "validés par écrit" in context.document_context
    assert "validés oralement" in context.memory_context


def test_memory_retrieval_is_audited_without_content(tmp_path: Path) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []
    memory = _repository(tmp_path).create(_draft(), "admin")

    retriever = CORE.create_retriever(tmp_path, lambda event, actor, details: events.append((event, actor, details)))
    builder = CORE.ContextBuilder(CORE.GlobalAgentPolicy(("Politique",)), retriever)
    builder.build(CORE.default_agents()[0], CORE.ApplicationIdentity(application_id="arcenal-system", user_id="admin"), None, {}, "Pourquoi SilverBullet ?")

    event = next(item for item in events if item[0] == "memory.retrieve")
    assert event[2]["memory_ids"] == [memory.id]
    assert "SilverBullet est retenu" not in str(event[2])


def test_ats_cannot_retrieve_confidential_accounting_memory(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    repository.create(_draft(scopes=("accounting",), confidentiality="confidential", content="Résultat financier confidentiel : 999 euros."), "admin")

    context = _context(tmp_path, CORE.default_agents()[1], "arcenal-ats", "Quels sont les derniers résultats financiers ?")

    assert context.sources == ()
    assert "999 euros" not in context.knowledge_context


def test_ats_retrieves_only_compatible_company_memory(tmp_path: Path) -> None:
    _repository(tmp_path).create(_draft(scopes=("company", "recruitment"), content="Le projet ATS utilise un entretien structuré."), "admin")

    context = _context(tmp_path, CORE.default_agents()[1], "arcenal-ats", "Quel entretien utilise le projet ATS ?")

    assert any(source.source_type is CORE.SourceType.ENTERPRISE_MEMORY for source in context.sources)
    assert "entretien structuré" in context.memory_context


def test_agent_origin_requires_review_before_rag(tmp_path: Path) -> None:
    draft = _draft().model_copy(update={"provenance": CORE.MemoryProvenance(source_type=CORE.MemorySourceType.AGENT, source_id="agent-arc", recorded_at=datetime.now(timezone.utc), agent_id="arc")})
    repository = _repository(tmp_path)
    memory = repository.create(draft.model_copy(update={"status": CORE.MemoryStatus.PENDING_REVIEW}), "arc")

    context = _context(tmp_path, CORE.default_agents()[0], "arcenal-system", "Pourquoi SilverBullet ?")

    assert memory.status is CORE.MemoryStatus.PENDING_REVIEW
    assert context.sources == ()


def _api_module() -> ModuleType:
    source = Path(__file__).parents[2] / "plugins" / "arcenal-supervisor" / "dashboard" / "enterprise_memory_api.py"
    spec = importlib.util.spec_from_file_location("arcenal_enterprise_memory_api_test", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("L’API mémoire est introuvable.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_memory_api_requires_admin_and_physical_delete_confirmation(tmp_path: Path) -> None:
    module = _api_module()
    app = FastAPI()
    app.include_router(module.router)
    client = TestClient(app)
    payload = {"memory_type": "fact", "summary": "Paie", "content": "ONYX utilise SILAE.", "source_type": "manual", "source_id": "admin-1", "knowledge_scopes": ["company"]}
    with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path), "ARCENAL_AUDIT_DIR": str(tmp_path / "audit")}):
        unauthorized = client.get("/memory/v1")
        created = client.post("/memory/v1", headers={"Remote-User": "admin"}, json=payload)
        memory_id = created.json()["entry"]["id"]
        filtered = client.get("/memory/v1?memory_type=fact&scope=company", headers={"Remote-User": "admin"})
        invalid = client.get("/memory/v1?memory_type=unknown", headers={"Remote-User": "admin"})
        generated = client.post("/memory/v1", headers={"Remote-User": "admin"}, json={**payload, "source_type": "agent", "source_id": "arc-1", "summary": "Suggestion ARC"})
        refused = client.request("DELETE", f"/memory/v1/{memory_id}", headers={"Remote-User": "admin"}, json={"confirmed": False, "physical": True, "reason": "Droit à l’oubli"})
        deleted = client.request("DELETE", f"/memory/v1/{memory_id}", headers={"Remote-User": "admin"}, json={"confirmed": True, "physical": True, "reason": "Droit à l’oubli"})

    assert unauthorized.status_code == 401
    assert created.status_code == 201
    assert [item["id"] for item in filtered.json()["entries"]] == [memory_id]
    assert invalid.status_code == 422
    assert generated.json()["entry"]["status"] == "pending_review"
    assert refused.status_code == 409
    assert deleted.json() == {"deleted": True, "physical": True}
