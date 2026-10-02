"""Registre métier des agents ARCenal."""

from .errors import AgentContractError, AgentDisabledError, AgentNotFoundError
from .frugal_models import ModelAvailability, ModelLocation
from .model_router import ModelRegistry
from .models import AgentDefinition, AgentUpdate, ModelPolicy
from .repository import AgentRepository


class AgentManager:
    def __init__(self, repository: AgentRepository, models: ModelRegistry | None = None) -> None:
        self._repository = repository
        self._models = models

    def list_agents(self) -> tuple[AgentDefinition, ...]:
        return tuple(sorted(self._repository.load(), key=lambda item: item.id))

    def get(self, agent_id: str, *, require_enabled: bool = False) -> AgentDefinition:
        agent = next((item for item in self._repository.load() if item.id == agent_id), None)
        if agent is None:
            raise AgentNotFoundError(f"Agent inconnu : {agent_id}.")
        if require_enabled and not agent.enabled:
            raise AgentDisabledError(f"L’agent {agent_id} est désactivé.")
        return agent

    def register(self, agent: AgentDefinition) -> AgentDefinition:
        agents = self._repository.load()
        if any(item.id == agent.id for item in agents):
            raise ValueError(f"L’agent {agent.id} est déjà enregistré.")
        self._validate_policy(agent.model_policy)
        self._repository.save((*agents, agent))
        return agent

    def update(self, agent_id: str, update: AgentUpdate) -> AgentDefinition:
        current = self.get(agent_id)
        values = self._update_values(update)
        replacement = current.model_copy(update=values)
        self._validate_policy(replacement.model_policy)
        agents = tuple(replacement if item.id == agent_id else item for item in self._repository.load())
        self._repository.save(agents)
        return replacement

    def _update_values(self, update: AgentUpdate) -> dict[str, object]:
        values: dict[str, object] = {}
        if update.autonomy_level is not None:
            values["autonomy_level"] = update.autonomy_level
        if update.enabled is not None:
            values["enabled"] = update.enabled
        if update.model_policy is not None:
            values["model_policy"] = update.model_policy
        return values

    def _validate_policy(self, policy: ModelPolicy) -> None:
        if policy.mode != "fixed" or self._models is None:
            return
        model = self._models.get(policy.allowed_models[0])
        if model is None or not model.enabled or model.availability is ModelAvailability.UNAVAILABLE:
            raise AgentContractError("Le modèle FIXED doit être activé dans le registre ARC.")
        if model.provider != policy.allowed_providers[0]:
            raise AgentContractError("Le fournisseur FIXED ne correspond pas au modèle sélectionné.")
        if policy.local_only and model.location is not ModelLocation.LOCAL:
            raise AgentContractError("Une politique locale ne peut pas sélectionner un modèle distant.")
