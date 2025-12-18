from typing import Optional
from agno.agent import Agent
from pydantic import BaseModel


def create_agent(llm, prompt: Optional[str] = None) -> Agent:
    """
    通用agent初始化
    """
    return Agent(
        name="common Agent",
        model=llm,
        instructions=(prompt),
    )
