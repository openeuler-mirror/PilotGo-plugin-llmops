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

def create_schema_agent(llm, schema: Optional[BaseModel] = None, prompt: Optional[str] = None) -> Agent:
    """
    Passing Output Schema to the agent
    """
    return Agent(
        name="Schema Agent",
        model=llm,
        output_schema=schema,
        instructions=(prompt),
    )