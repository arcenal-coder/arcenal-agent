"""Registre métier des agents ARCenal."""

from .errors import AgentDisabledError, AgentNotFoundError
from .models import AgentDefinition, AgentUpdate
from .repository import AgentRepository


class AgentManager:
    def __init__(self, repository: AgentRepository) -> None:
        self._repository = repository

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
        self._repository.save((*agents, agent))
        return agent

    def update(self, agent_id: str, update: AgentUpdate) -> AgentDefinition:
        current = self.get(agent_id)
        values = update.model_dump(exclude_none=True)
        replacement = current.model_copy(update=values)
        agents = tuple(replacement if item.id == agent_id else item for item in self._repository.load())
        self._repository.save(agents)
        return replacement
