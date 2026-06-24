from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.common.errors import AgentNotFoundError
from app.common.logger import get_logger
from app.domain.parameter.ChatParam import AgentRequest, AgentResponse
from app.service.agent_service import AgentService

logger = get_logger(__name__)

router = APIRouter(tags=["KyAgentOps"])


def _get_service(request: Request) -> AgentService:
    service: AgentService | None = getattr(request.app.state, "agent_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="agent service not initialized")
    return service


@router.post("/run_agent")
async def run_agent(
    req: AgentRequest,
    service: AgentService = Depends(_get_service),
) -> AgentResponse:

    try:
        result = await service.run(req.agent, req.message)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"agent '{req.agent}' not found")
    return AgentResponse(agent=req.agent, response=result)


@router.get("/list_agents")
async def list_agents(service: AgentService = Depends(_get_service)) -> list[dict[str, str]]:
    """List registered agents with their names and types."""
    return service.list_agent_summaries()
