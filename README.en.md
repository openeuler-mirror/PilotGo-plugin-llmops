# PilotGo-plugin-llmops

## Description

PilotGo-plugin-llmops is an LLM-powered AIOps plugin for PilotGo. Leveraging large language models and agent orchestration, it delivers cluster fault analysis, inspection, and operation & maintenance management. It combines natural-language interaction, knowledge retrieval, MCP tool invocation, and a visual console so operators can monitor, diagnose, and remediate clusters through conversation.

The project is composed of four loosely-coupled submodules that together form a complete AI-driven operations pipeline:

- **agent** — a Python + FastAPI + [Agno](https://github.com/agno-agi/agno) AI agent service. Handles agent orchestration, model adaptation, skill/knowledge-base/MCP-tool integration, and conversation execution.
- **server** — a Go + Gin + GORM backend. Exposes RESTful APIs for projects, knowledge bases, audit, topology, and operation scripts, plus an MCP streamable HTTP endpoint.
- **mcps** — a Python + [FastMCP](https://github.com/jlowin/fastmcp) MCP toolset. Auto-discovers and registers OS-level operations tools (process, Nginx, network, hardware resources, audit logs, etc.).
- **web** — a Vue 3 + TypeScript + Vite console. Visual management for project overview, cluster topology, monitoring, events, operations, knowledge base, and audit.

## Tech Stack

| Module | Language / Runtime | Key dependencies |
| --- | --- | --- |
| agent | Python ≥ 3.11 (uv-managed) | FastAPI, Uvicorn, Agno, OpenAI/Ollama/DashScope SDK, ChromaDB |
| server | Go 1.25 | Gin, GORM/MySQL, MinIO, modelcontextprotocol/go-sdk |
| mcps | Python | FastMCP (stdio transport) |
| web | Node.js ^20.19 / ≥22.12 | Vue 3, Vite, Element Plus, Pinia, Vue Router, ECharts, @antv/g6, Tailwind CSS, vue-i18n |

## Code Organization

```
PilotGo-plugin-llmops/
├── agent/                      # AI agent service (Python)
│   ├── main.py                 # Entry: builds FastAPI app (AgentOS/Playground)
│   ├── pyproject.toml          # uv dependency manifest
│   ├── README.md               # agent startup guide
│   └── app/
│       ├── agent_orchestration/  # Agent orchestration: topological build & dependency resolution
│       │   ├── builder.py        #   Builds agents/teams/workflows in dependency order per agent.yaml
│       │   └── agents/           #   Agent definitions (agent.yaml + agent.py + optional mcp/skill/knowledge.json)
│       │       ├── ops_agent/    #   General ops agent (with MCP & skills)
│       │       ├── qa_agent/     #   Knowledge-retrieval agent (with knowledge base)
│       │       └── template_agent/#   Agent template
│       ├── common/               # Shared: config, builder utils, errors, file readers, logger, vector DB adapter
│       │   ├── config/           #   AgentConfig parsing
│       │   └── vectordb_adapter/ #   RAGFlow vector DB adapter
│       ├── domain/parameter/     # Request/response params (ChatParam)
│       ├── extensions/           # Extensions: knowledge, MCP, skills
│       │   ├── knowledge/        #   Knowledge base health check & config
│       │   ├── mcp/              #   MCP server probing and bundled mcp_time/weather
│       │   └── skill/            #   Skills (find-skills, k8s-manage, web-design-guidelines)
│       ├── llm_adapter/          # LLM adapter (OpenAI-compatible)
│       ├── router/               # FastAPI routers (/run_agent, /list_agents)
│       └── service/              # AgentService: registry & request dispatch
├── mcps/                        # MCP toolset (Python + FastMCP, stdio)
│   ├── main.py                 # Auto-scans os/*.py and registers each as an MCP tool
│   └── os/                     # OS operations tools, grouped by domain
│       ├── app_mgmt/           #   App/package management (rpm/deb/pip/npm/flatpak, ...)
│       ├── audit_logs/         #   Audit logs
│       ├── hw_resources/       #   Hardware resources
│       ├── net_mgmt/           #   Network management
│       ├── ngx_mgmt/           #   Nginx config/log/runtime management
│       ├── oom_analysis/       #   OOM analysis
│       ├── perf_monitor/       #   Performance monitoring
│       ├── proc_mgmt/          #   Process management (/proc parsing, process tree, top, ...)
│       ├── redis_mgmt/         #   Redis management
│       └── version_control/    #   Version control
├── server/                     # Backend service (Go + Gin + GORM)
│   ├── cli/server/main.go      # Entry: load config → init DB → start services → start HTTP
│   ├── go.mod / go.sum
│   ├── config.yaml(.templete)   # Server config (server/db/log/minio)
│   ├── config/                 # Config loading (YAML)
│   ├── db/                     # MySQL (GORM) connection & migration
│   ├── http/                   # HTTP server, routers, handlers, MCP endpoint
│   │   ├── server.go           #   Merges Gin handler with MCP streamable HTTP
│   │   ├── router.go           #   /api/project /knowledge /audit /topology ...
│   │   ├── handler/            #   Business handlers
│   │   └── mcp_handler/        #   MCP tool handlers
│   ├── service/                # Business service layer
│   │   ├── service.go          #   Service registry & lifecycle
│   │   ├── project/            #   Project management
│   │   ├── knowledge/          #   Knowledge base (MinIO object storage)
│   │   ├── audit/               #   Audit logs
│   │   ├── topology/            #   Topology config
│   │   └── operation/          #   Operation scripts
│   ├── logger/                 # Logging component
│   └── scripts/                # Local dev scripts (start/stop/status, includes MinIO)
└── web/                        # Frontend console (Vue 3 + TS + Vite)
    ├── package.json / vite.config.ts
    ├── README.md               # Frontend guide
    └── src/
        ├── main.ts / App.vue   # Entry & layout (top bar + side nav + router view)
        ├── router/             # Routes (/ overview, /project/:id detail)
        ├── views/              # Pages: Overview (project list), Project (detail)
        ├── components/
        │   ├── ProjectCard.vue #   Project card
        │   ├── common/          #   Common components (MTable, StatusTag)
        │   └── project/         #   Project sub-pages (Topology/Monitor/Event/Operation/Knowledge/Audit)
        ├── apis/               # Backend API wrappers (request.ts is the unified HttpClient)
        ├── stores/             # Pinia state management (project)
        ├── utils/              # Utilities (queryString, topologyGraph)
        └── locales/            # vue-i18n locales (zh / en)
```

## Quick Start

See each submodule's `README.md` for full requirements and commands:

- **server** — copy `server/config.yaml.templete` to `server/config.yaml` and fill in DB/MinIO credentials, then run `server/scripts/restart-services.sh all` to bring up MinIO and the backend together (listens on `:7070` by default).
- **agent** — `cd agent/`, `uv sync` to install dependencies, then `uv run python main.py` (defaults to `0.0.0.0:8000`). See `agent/README.md` for environment variables.
- **mcps** — consumed by the agent as a stdio MCP server; tools are auto-loaded from `mcps/os/`.
- **web** — `cd web/`, `yarn` to install dependencies, `yarn dev` to start the dev server (default `http://localhost:4100`). See `web/README.md` and `web/.env.example` for backend proxy and API configuration.

## Contribution

1. Fork the repository
2. Create a `Feat_xxx` branch
3. Commit your code
4. Create a Pull Request
