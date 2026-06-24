import os

import uvicorn
from agno.os import AgentOS
from app.agent_orchestration import build_agents, list_agent_configs
from app.router import RegisterRouterList
from app.service.agent_service import AgentService
from dotenv import load_dotenv

load_dotenv()

def _register_routers(app):
    """Register routers listed in app.router.RegisterRouterList."""
    for router_module in RegisterRouterList:
        router = getattr(router_module, "router", None)
        if router is not None:
            app.include_router(router)


def _partition_runtime_objects(objects: list[object]) -> tuple[list[object], list[object], list[object]]:
    agents: list[object] = []
    teams: list[object] = []
    workflows: list[object] = []
    for obj in objects:
        if hasattr(obj, "initialize_agent"):
            agents.append(obj)
            continue
        if hasattr(obj, "initialize_team"):
            teams.append(obj)
            continue
        if hasattr(obj, "initialize_workflow"):
            workflows.append(obj)
            continue
        agents.append(obj)
    return agents, teams, workflows


def _build_app(use_playground: bool = False):
    """Build the FastAPI application and attach the AgentService."""
    agents = build_agents(list_agent_configs())
    agentos_agents, agentos_teams, agentos_workflows = _partition_runtime_objects(agents)

    if use_playground:
        try:
            from agno.playground import Playground

            app = Playground(
                agents=agentos_agents,
                teams=agentos_teams,
                workflows=agentos_workflows,
            ).get_app()
        except Exception:
            app = AgentOS(
                agents=agentos_agents,
                teams=agentos_teams,
                workflows=agentos_workflows,
            ).get_app()
    else:
        app = AgentOS(
            agents=agentos_agents,
            teams=agentos_teams,
            workflows=agentos_workflows,
        ).get_app()

    app.state.agent_service = AgentService(agents)
    _register_routers(app)
    return app


APP_ENV = os.getenv("APP_ENV", "dev").strip().lower()
app = _build_app(use_playground=APP_ENV not in {"prod", "production"})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = APP_ENV in {"dev", "development"}
    # uvicorn.run("main:app", host=host, port=port, reload=reload)
    # IDE debug时切换为非reload模式
    uvicorn.run("main:app", host=host, port=port)
