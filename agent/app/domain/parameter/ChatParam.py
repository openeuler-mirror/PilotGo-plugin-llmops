from __future__ import annotations

from pydantic import BaseModel


class AgentRequest(BaseModel):
    agent: str
    message: str


class AgentResponse(BaseModel):
    agent: str
    response: str
