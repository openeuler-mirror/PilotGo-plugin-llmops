from __future__ import annotations

from copy import deepcopy
from typing import Any

from agno.agent import Agent

from app.common.agent_builder_utils import load_knowledge_config, load_mcp_config
from app.common.config.agent_config import AgentConfig
from app.llm_adapter.openai_adapter import get_model


def build(config: AgentConfig, refs: list[Any] | None = None) -> Any:
    if refs:
        raise ValueError(f"{config.name} does not accept build refs")

    # Explicit Agno Agent build config.
    kwargs: dict[str, Any] = {
        "name": config.name,
        "description": config.description,
        "instructions": config.instructions,
        "model": get_model(config.model),
        "markdown": True,
        "id": config.id,
    }
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    load_knowledge_config(kwargs, config)
    return Agent(**kwargs)
