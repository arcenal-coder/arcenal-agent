"""Registre métier des agents ARCenal."""

from .context import required_confidentiality
from .errors import AgentContractError, AgentDisabledError, AgentNotFoundError
from .frugal_models import ModelAvailability, ModelLocation
from .knowledge_models import ConfidentialityLevel
from .model_router import ModelRegistry
from .models import AgentDefinition, AgentUpdate
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
        self._validate_policy(agent)
        self._repository.save((*agents, agent))
        return agent

    def update(self, agent_id: str, update: AgentUpdate) -> AgentDefinition:
        current = self.get(agent_id)
        values = self._update_values(update)
        replacement = current.model_copy(update=values)
        self._validate_policy(replacement)
        agents = tuple(replacement if item.id == agent_id else item for item in self._repository.load())
        self._repository.save(agents)
        return replacement

    def _update_values(self, update: AgentUpdate) -> dict[str, object]:
        values: dict[str, object] = {}
        if update.autonomy_level is not None:
            values["autonomy_level"] = update.autonomy_level
        if update.enabled is not None:
            values["enabled"] = update.enabled
        if update.harness is not None:
            values["harness"] = update.harness
        if update.model_policy is not None:
            values["model_policy"] = update.model_policy
        return values

    def _validate_policy(self, agent: AgentDefinition) -> None:
        policy = agent.model_policy
        if policy.mode != "fixed" or self._models is None:
            return
        model = self._models.get(policy.allowed_models[0])
        if model is None or not model.enabled or model.availability is ModelAvailability.UNAVAILABLE:
            raise AgentContractError("Le modèle FIXED doit être activé dans le registre ARC.")
        if model.provider != policy.allowed_providers[0]:
            raise AgentContractError("Le fournisseur FIXED ne correspond pas au modèle sélectionné.")
        if policy.local_only and model.location is not ModelLocation.LOCAL:
            raise AgentContractError("Une politique locale ne peut pas sélectionner un modèle distant.")
        self._validate_privacy(agent, model.privacy_class)

    def _validate_privacy(self, agent: AgentDefinition, privacy_class: ConfidentialityLevel) -> None:
        required = required_confidentiality(agent.permissions)
        levels = {"public": 0, "internal": 1, "restricted": 2, "confidential": 3, "admin": 4}
        if levels[privacy_class.value] < levels[required.value]:
            raise AgentContractError("Le modèle FIXED n’autorise pas le niveau de confidentialité requis par cet agent.")
