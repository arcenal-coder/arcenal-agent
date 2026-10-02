"""Administration bornée de la mémoire isolée des agents ARCenal."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Annotated, Literal, Protocol, cast

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator


router = APIRouter(prefix="/agents")
root_router = APIRouter(prefix="/api/v1/agents")
PROFILE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _load_arc_core() -> ModuleType:
    name = "arcenal_arc_core"
    if name in sys.modules:
        return sys.modules[name]
    source = Path(__file__).parents[1] / "arc_core" / "__init__.py"
    spec = spec_from_file_location(name, source, submodule_search_locations=[str(source.parent)])
    if spec is None or spec.loader is None:
        raise RuntimeError("ARC Core est introuvable.")
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE = _load_arc_core()
AgentQueryResponseModel = CORE.AgentQueryResponse


class AgentMemoryUpdate(BaseModel):
    """Contenu Markdown borné de la mémoire propre à un agent."""

    content: str = Field(max_length=100_000)


class AgentMemoryResponse(BaseModel):
    """Mémoire présentable sans exposer le reste du profil."""

    content: str
    profile: str
    updated_at: str | None


class ProfileHarnessWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    context: str = Field(default="", max_length=16_000)
    directives: str = Field(default="", max_length=16_000)
    memory: str = Field(default="", max_length=32_000)


class ProfileHarnessResponse(ProfileHarnessWrite):
    profile: str


class AgentQueryRequest(BaseModel):
    """Message applicatif borné, sans politique contrôlée par le client."""

    model_config = ConfigDict(extra="forbid", strict=True)
    message: str = Field(min_length=1, max_length=20_000)
    session_id: str | None = Field(default=None, max_length=128)
    context: dict[str, str] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20 or any(len(key) > 64 or len(item) > 2_000 for key, item in value.items()):
            raise ValueError("Le contexte applicatif dépasse les limites autorisées.")
        return value


class AgentInstructionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    content: str = Field(min_length=1, max_length=8_000)


class AgentHarnessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    context: str = Field(default="", max_length=16_000)
    directives: str = Field(default="", max_length=16_000)
    memory: str = Field(default="", max_length=32_000)


class AgentModelPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    mode: Literal["auto", "fixed"] = "auto"
    preferred_capability: Literal["deterministic", "light", "standard", "advanced", "specialized"] = "standard"
    local_preferred: bool = True
    allowed_providers: list[str] = Field(default_factory=list)
    denied_providers: list[str] = Field(default_factory=list)
    allowed_models: list[str] = Field(default_factory=list)
    local_only: bool = False
    max_cost: float | None = Field(default=None, ge=0)


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=500)
    role: str = Field(min_length=1, max_length=80)
    application: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    harness: AgentHarnessRequest = Field(default_factory=AgentHarnessRequest)
    system_instructions: list[AgentInstructionRequest] = Field(min_length=1)
    permissions: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    knowledge_scopes: list[str] = Field(min_length=1)
    model_policy: AgentModelPolicyRequest = Field(default_factory=AgentModelPolicyRequest)
    autonomy_level: Literal["automatic", "controlled", "approval_required"]
    enabled: bool = True
    metadata: dict[str, str] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    autonomy_level: Literal["automatic", "controlled", "approval_required"] | None = None
    enabled: bool | None = None
    harness: AgentHarnessRequest | None = None
    model_policy: AgentModelPolicyRequest | None = None


class AgentRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: str = Field(default="", max_length=20_000)


class AgentRuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    agent_id: str
    mode: Literal["auto", "fixed"]
    model: str
    provider: str
    registry_id: str


class ModelPolicyLike(Protocol):
    mode: str
    preferred_capability: object
    allowed_providers: tuple[str, ...]
    denied_providers: tuple[str, ...]
    allowed_models: tuple[str, ...]
    local_only: bool
    local_preferred: bool
    max_cost: float | None


class AgentDefinitionLike(Protocol):
    id: str
    permissions: tuple[str, ...]
    tools: tuple[str, ...]
    model_policy: ModelPolicyLike


class RoutingDecisionLike(Protocol):
    model: str
    provider: str
    registry_id: str


def _registry_path() -> Path:
    from hermes_constants import get_hermes_home

    return get_hermes_home() / "arcenal" / "agents.json"


def _manager():
    repository = CORE.AgentRepository(_registry_path(), CORE.default_agents())
    CORE.migrate_legacy_harness(repository, _registry_path().parent / "managed-files")
    runtime = _frugal_runtime()
    return CORE.AgentManager(repository, runtime.registry)


def _frugal_runtime():
    runtime = CORE.FrugalRuntime(_registry_path().parent / "frugal")
    runtime.ensure_configured_model()
    return runtime


def _routing_need(agent: AgentDefinitionLike, message: str) -> object:
    task_type = CORE.classify_task(message)
    required = CORE.required_capability(task_type, message)
    capability = agent.model_policy.preferred_capability if agent.model_policy.mode == "fixed" else required
    if capability is CORE.CapabilityProfile.DETERMINISTIC:
        capability = CORE.CapabilityProfile.STANDARD
    policy = agent.model_policy
    confidentiality = CORE.required_confidentiality(agent.permissions)
    return CORE.RoutingNeed(agent_id=agent.id, task_type=task_type, required_capability=capability, confidentiality=confidentiality, tools_required=bool(agent.tools), allowed_providers=policy.allowed_providers, denied_providers=policy.denied_providers, allowed_models=policy.allowed_models, local_only=policy.local_only, local_preferred=policy.local_preferred, max_cost=policy.max_cost)


def _runtime_selection(agent_id: str, message: str) -> AgentRuntimeResponse:
    agent = cast(AgentDefinitionLike, _manager().get(agent_id))
    runtime = _frugal_runtime()
    router = CORE.ModelRouter(runtime.registry, providers=runtime.providers)
    decision = cast(RoutingDecisionLike, router.route(_routing_need(agent, message)))
    mode: Literal["auto", "fixed"] = "fixed" if agent.model_policy.mode == "fixed" else "auto"
    return AgentRuntimeResponse(agent_id=agent.id, mode=mode, model=decision.model, provider=decision.provider, registry_id=decision.registry_id)


def _agent_definition(request: AgentCreateRequest):
    policy = _model_policy(request.model_policy)
    instructions = tuple(CORE.InstructionBlock(**item.model_dump()) for item in request.system_instructions)
    permissions = tuple(CORE.Permission(item) for item in request.permissions)
    return CORE.AgentDefinition(
        id=request.id, name=request.name, description=request.description,
        role=request.role, application=request.application, enabled=request.enabled,
        harness=CORE.AgentHarness(**request.harness.model_dump()),
        tools=tuple(request.tools), knowledge_scopes=tuple(request.knowledge_scopes), metadata=request.metadata,
        autonomy_level=CORE.AutonomyLevel(request.autonomy_level), model_policy=policy,
        permissions=permissions, system_instructions=instructions,
    )


def _model_policy(request: AgentModelPolicyRequest):
    return CORE.ModelPolicy(
        mode=request.mode, preferred_capability=CORE.CapabilityProfile(request.preferred_capability),
        local_preferred=request.local_preferred,
        allowed_providers=tuple(request.allowed_providers),
        denied_providers=tuple(request.denied_providers),
        allowed_models=tuple(request.allowed_models),
        local_only=request.local_only, max_cost=request.max_cost,
    )


def _agent_update(request: AgentUpdateRequest):
    autonomy = CORE.AutonomyLevel(request.autonomy_level) if request.autonomy_level else None
    harness = CORE.AgentHarness(**request.harness.model_dump()) if request.harness else None
    policy = _model_policy(request.model_policy) if request.model_policy else None
    return CORE.AgentUpdate(autonomy_level=autonomy, enabled=request.enabled, harness=harness, model_policy=policy)


def _audit_writer(event: str, actor: str, details: dict[str, object]) -> object:
    from arcenal_arc_core.audit_adapter import append_agent_event

    return append_agent_event(event, actor, details)


def _arc_core():
    policy = CORE.GlobalAgentPolicy(instructions=("Refuser par défaut toute permission absente du contrat de l’agent.", "Ne jamais exposer de secret et conserver les validations des actions sensibles."))
    from hermes_constants import get_hermes_home

    retriever = CORE.create_retriever(get_hermes_home(), _audit_writer)
    builder = CORE.ContextBuilder(policy, retriever)
    runtime = _frugal_runtime()
    return CORE.ArcCore(_manager(), builder, runtime.engine, _audit_writer)


def query_dashboard_agent(agent_id: str, message: str, session_id: str, user_id: str) -> object:
    if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}", user_id):
        raise CORE.ApplicationAuthenticationError("Identité administrateur YunoHost invalide.")
    caller = CORE.ApplicationIdentity(
        application_id="arcenal-system", user_id=user_id,
        user_source=CORE.UserIdentitySource.YUNOHOST,
    )
    return _arc_core().query(agent_id, caller, message, session_id)


def _translate_error(exc: Exception) -> HTTPException:
    from arcenal_arc_core.errors import AgentAccessDeniedError, AgentContractError, AgentDisabledError, AgentExecutionError, AgentNotFoundError, ApplicationAuthenticationError, ModelRoutingError, ProviderExecutionError

    if isinstance(exc, AgentNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, AgentDisabledError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ApplicationAuthenticationError):
        return HTTPException(status_code=401, detail=str(exc))
    if isinstance(exc, AgentAccessDeniedError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, (AgentContractError, ValueError)):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ModelRoutingError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, (AgentExecutionError, ProviderExecutionError)):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="ARC Core a rencontré une erreur interne.")


def _profile_dir(name: str) -> Path:
    if not PROFILE_NAME_PATTERN.fullmatch(name) or name == "default":
        raise HTTPException(status_code=422, detail="Identifiant d’agent invalide.")
    from hermes_cli import profiles as profiles_mod

    profile = next((item for item in profiles_mod.list_profiles() if item.name == name), None)
    if profile is None:
        raise HTTPException(status_code=404, detail="Agent introuvable.")
    return Path(profile.path).resolve()


def _memory_path(name: str) -> Path:
    root = _profile_dir(name).resolve()
    path = root / "memories" / "MEMORY.md"
    if root not in path.resolve().parents:
        raise HTTPException(status_code=422, detail="Chemin de mémoire invalide.")
    return path


def _harness_paths(name: str) -> dict[str, Path]:
    root = _profile_dir(name).resolve()
    paths = {
        "context": root / "CONTEXT.md",
        "directives": root / "DIRECTIVES.md",
        "memory": root / "memories" / "MEMORY.md",
    }
    if any(root not in path.resolve().parents for path in paths.values()):
        raise HTTPException(status_code=422, detail="Chemin de harnais invalide.")
    return paths


def _read_profile_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.is_file() else ""
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Paramètre de l’agent illisible.") from exc


def _write_profile_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Paramètre de l’agent impossible à enregistrer.") from exc


def _read_harness(name: str) -> ProfileHarnessResponse:
    paths = _harness_paths(name)
    return ProfileHarnessResponse(profile=name, **{key: _read_profile_text(path) for key, path in paths.items()})


def _write_harness(name: str, payload: ProfileHarnessWrite) -> ProfileHarnessResponse:
    paths = _harness_paths(name)
    for key, path in paths.items():
        _write_profile_text(path, getattr(payload, key))
    return _read_harness(name)


def _read_memory(name: str) -> AgentMemoryResponse:
    path = _memory_path(name)
    try:
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        updated_at = path.stat().st_mtime if path.is_file() else None
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Mémoire de l’agent illisible.") from exc
    timestamp = datetime.fromtimestamp(updated_at, timezone.utc).isoformat() if updated_at is not None else None
    return AgentMemoryResponse(content=content, profile=name, updated_at=timestamp)


def _write_memory(name: str, content: str) -> AgentMemoryResponse:
    path = _memory_path(name)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".memory.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(temporary, path)
        path.chmod(0o600)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Mémoire de l’agent impossible à enregistrer.") from exc
    return _read_memory(name)


@router.get("/{name}/memory", response_model=AgentMemoryResponse)
def get_agent_memory(name: str) -> AgentMemoryResponse:
    return _read_memory(name)


@router.put("/{name}/memory", response_model=AgentMemoryResponse)
def update_agent_memory(name: str, request: AgentMemoryUpdate) -> AgentMemoryResponse:
    return _write_memory(name, request.content)


@router.get("/{name}/harness", response_model=ProfileHarnessResponse)
def get_profile_harness(name: str) -> ProfileHarnessResponse:
    return _read_harness(name)


@router.put("/{name}/harness", response_model=ProfileHarnessResponse)
def update_profile_harness(name: str, request: ProfileHarnessWrite) -> ProfileHarnessResponse:
    return _write_harness(name, request)


@router.get("/registry")
def list_registered_agents() -> dict[str, object]:
    return {"agents": [agent.model_dump(mode="json") for agent in _manager().list_agents()]}


@router.post("/registry", status_code=201)
def create_registered_agent(request: AgentCreateRequest) -> dict[str, object]:
    try:
        return _manager().register(_agent_definition(request)).model_dump(mode="json")
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.get("/registry/{agent_id}")
def get_registered_agent(agent_id: str) -> dict[str, object]:
    try:
        return _manager().get(agent_id).model_dump(mode="json")
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.patch("/registry/{agent_id}")
def update_registered_agent(agent_id: str, request: AgentUpdateRequest) -> dict[str, object]:
    try:
        return _manager().update(agent_id, _agent_update(request)).model_dump(mode="json")
    except Exception as exc:
        raise _translate_error(exc) from exc


@router.post("/registry/{agent_id}/runtime", response_model=AgentRuntimeResponse)
def resolve_agent_runtime(agent_id: str, request: AgentRuntimeRequest) -> AgentRuntimeResponse:
    try:
        return _runtime_selection(agent_id, request.message)
    except Exception as exc:
        raise _translate_error(exc) from exc


@root_router.post("/{agent_id}/query", response_model=AgentQueryResponseModel)
def query_agent(
    agent_id: str,
    request: AgentQueryRequest,
    application_id: Annotated[str, Header(alias="X-ARCenal-Application")],
    authorization: Annotated[str | None, Header()] = None,
    user_id: Annotated[str | None, Header(alias="X-ARCenal-User")] = None,
    remote_user: Annotated[str | None, Header(alias="Remote-User")] = None,
    x_remote_user: Annotated[str | None, Header(alias="X-Remote-User")] = None,
) -> AgentQueryResponseModel:
    from arcenal_arc_core.auth import ApplicationAuthenticator

    try:
        platform_user = remote_user or x_remote_user
        if platform_user and user_id and platform_user != user_id:
            raise CORE.ApplicationAuthenticationError("L’identité utilisateur transmise ne correspond pas à la session YunoHost.")
        resolved_user = platform_user or user_id
        source = CORE.UserIdentitySource.YUNOHOST if platform_user else CORE.UserIdentitySource.APPLICATION
        caller = ApplicationAuthenticator().authenticate(application_id, authorization, resolved_user, source)
        return _arc_core().query(
            agent_id,
            caller,
            request.message,
            request.session_id,
            request.context,
        )
    except Exception as exc:
        raise _translate_error(exc) from exc
