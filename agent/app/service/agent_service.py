from typing import Any
import inspect

from app.common.errors import AgentNotFoundError
from app.common.logger import get_logger

logger = get_logger(__name__)


class AgentService:
    """Manages a registry of agents and dispatches run requests."""

    def __init__(self, agents: list[Any]) -> None:
        self._registry: dict[str, Any] = {a.name: a for a in agents}

    def get_agent(self, name: str) -> Any:
        agent = self._registry.get(name)
        if agent is None:
            raise AgentNotFoundError(f"agent '{name}' not found")
        return agent

    def list_agents(self) -> list[str]:
        return list(self._registry.keys())

    def list_agent_summaries(self) -> list[dict[str, str]]:
        summaries: list[dict[str, str]] = []
        for name, agent in self._registry.items():
            summaries.append({"name": name, "type": type(agent).__name__.lower()})
        return summaries

    async def run(self, agent_name: str, message: str) -> str:
        """Run a message through the named agent and return the response text."""
        agent = self.get_agent(agent_name)
        logger.info("running agent=%s", agent_name)
        if hasattr(agent, "arun"):
            response = await agent.arun(message)
        elif hasattr(agent, "run"):
            response = agent.run(message)
            if inspect.isawaitable(response):
                response = await response
        else:
            raise TypeError(f"agent '{agent_name}' has neither arun nor run")
        return response.content if response else ""
