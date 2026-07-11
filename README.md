# PilotGo-plugin-llmops

## 介绍

PilotGo-plugin-llmops 是 PilotGo 的 LLM 智能运维插件，依托大语言模型（LLM）与 Agent 编排能力，提供集群故障分析、巡检与运维管理能力。它将自然语言交互、知识检索、MCP 工具调用与可视化控制台相结合，帮助运维人员通过对话完成集群的监控、诊断与处置。

项目由四个相对独立的子模块组成，协同提供完整的 AI 运维链路：

- **agent**：基于 Python + FastAPI + [Agno](https://github.com/agno-agi/agno) 的 AI Agent 服务，负责 Agent 编排、模型适配、技能/知识库/MCP 工具集成与对话执行。
- **server**：基于 Go + Gin + GORM 的后端服务，提供项目、知识库、审计、拓扑、运维脚本等 RESTful API，并暴露 MCP streamable HTTP 端点。
- **mcps**：基于 Python + [FastMCP](https://github.com/jlowin/fastmcp) 的 MCP 工具集，自动发现并注册面向 OS 层面的运维工具（进程、Nginx、网络、硬件资源、审计日志等）。
- **web**：基于 Vue 3 + TypeScript + Vite 的前端控制台，提供项目总览、集群拓扑、监控、事件、运维、知识库与审计的可视化管理。

## 技术栈

| 模块 | 语言/运行时 | 关键依赖 |
| --- | --- | --- |
| agent | Python ≥ 3.11（uv 管理） | FastAPI、Uvicorn、Agno、OpenAI/Ollama/DashScope SDK、ChromaDB |
| server | Go 1.25 | Gin、GORM/MySQL、MinIO、modelcontextprotocol/go-sdk |
| mcps | Python | FastMCP（stdio 传输） |
| web | Node.js ^20.19 / ≥22.12 | Vue 3、Vite、Element Plus、Pinia、Vue Router、ECharts、@antv/g6、Tailwind CSS、vue-i18n |

## 代码组织结构

```
PilotGo-plugin-llmops/
├── agent/                      # AI Agent 服务（Python）
│   ├── main.py                 # 入口：构建 FastAPI app（AgentOS/Playground）
│   ├── pyproject.toml          # uv 依赖声明
│   ├── README.md               # agent 启动说明
│   └── app/
│       ├── agent_orchestration/  # Agent 编排：拓扑构建、依赖解析
│       │   ├── builder.py        #   按 agent.yaml 拓扑序构建 agent/team/workflow
│       │   └── agents/           #   各 Agent 定义（agent.yaml + agent.py + 可选 mcp/skill/knowledge.json）
│       │       ├── ops_agent/    #   通用运维 Agent（含 MCP / 技能）
│       │       ├── qa_agent/     #   知识检索 Agent（含知识库）
│       │       └── template_agent/#   Agent 模板
│       ├── common/               # 公共能力：配置、构建工具、错误、文件读取、日志、向量库适配
│       │   ├── config/           #   AgentConfig 解析
│       │   └── vectordb_adapter/ #   RAGFlow 向量库适配
│       ├── domain/parameter/     # 请求/响应参数（ChatParam）
│       ├── extensions/           # 扩展能力：知识库、MCP、技能
│       │   ├── knowledge/        #   知识库健康检查与配置
│       │   ├── mcp/              #   MCP 服务探测及内置 mcp_time/weather
│       │   └── skill/            #   技能（find-skills、k8s-manage、web-design-guidelines）
│       ├── llm_adapter/          # LLM 适配（OpenAI 兼容）
│       ├── router/               # FastAPI 路由（/run_agent、/list_agents）
│       └── service/              # AgentService：注册表与请求分发
├── mcps/                        # MCP 工具集（Python + FastMCP，stdio）
│   ├── main.py                 # 自动扫描 os/ 下 *.py 并注册为 MCP 工具
│   └── os/                     # OS 运维工具，按域划分
│       ├── app_mgmt/           #   应用/包管理（rpm/deb/pip/npm/flatpak 等）
│       ├── audit_logs/         #   审计日志
│       ├── hw_resources/       #   硬件资源
│       ├── net_mgmt/           #   网络管理
│       ├── ngx_mgmt/           #   Nginx 配置/日志/运行状态管理
│       ├── oom_analysis/       #   OOM 分析
│       ├── perf_monitor/       #   性能监控
│       ├── proc_mgmt/          #   进程管理（/proc 解析、进程树、top 等）
│       ├── redis_mgmt/         #   Redis 管理
│       └── version_control/    #   版本控制
├── server/                     # 后端服务（Go + Gin + GORM）
│   ├── cli/server/main.go      # 入口：加载配置 → 初始化 DB → 启动服务 → 启动 HTTP
│   ├── go.mod / go.sum
│   ├── config.yaml(.templete)   # 服务配置（server/db/log/minio）
│   ├── config/                 # 配置加载（YAML）
│   ├── db/                     # MySQL（GORM）连接与迁移
│   ├── http/                   # HTTP 服务、路由、Handler、MCP 端点
│   │   ├── server.go           #   Gin + MCP streamable HTTP 合流
│   │   ├── router.go           #   /api/project /knowledge /audit /topology ...
│   │   ├── handler/            #   各业务 Handler
│   │   └── mcp_handler/        #   MCP 工具 Handler
│   ├── service/                # 业务服务层
│   │   ├── service.go          #   服务注册与生命周期
│   │   ├── project/            #   项目管理
│   │   ├── knowledge/          #   知识库（MinIO 对象存储）
│   │   ├── audit/               #   审计日志
│   │   ├── topology/            #   拓扑配置
│   │   └── operation/          #   运维脚本
│   ├── logger/                 # 日志组件
│   └── scripts/                # 本地开发脚本（启动/停止/状态，含 MinIO）
└── web/                        # 前端控制台（Vue 3 + TS + Vite）
    ├── package.json / vite.config.ts
    ├── README.md               # 前端说明
    └── src/
        ├── main.ts / App.vue   # 入口与布局（顶栏 + 侧栏 + 路由视图）
        ├── router/             # 路由（/ 总览，/project/:id 详情）
        ├── views/              # 页面：Overview（项目列表）、Project（详情）
        ├── components/
        │   ├── ProjectCard.vue #   项目卡片
        │   ├── common/          #   通用组件（MTable、StatusTag）
        │   └── project/         #   项目子页（Topology/Monitor/Event/Operation/Knowledge/Audit）
        ├── apis/               # 后端 API 封装（request.ts 为统一 HttpClient）
        ├── stores/             # Pinia 状态管理（project）
        ├── utils/              # 工具（queryString、topologyGraph）
        └── locales/            # vue-i18n 多语言（zh / en）
```

## 快速开始

各子模块的启动要求与命令详见对应目录下的 `README.md`：

- **server**：复制 `server/config.yaml.templete` 为 `server/config.yaml` 并填写数据库/MinIO 信息，使用 `server/scripts/restart-services.sh all` 一键拉起 MinIO 与后端（默认监听 `:7070`）。
- **agent**：进入 `agent/`，执行 `uv sync` 安装依赖后 `uv run python main.py` 启动（默认 `0.0.0.0:8000`），具体环境变量见 `agent/README.md`。
- **mcps**：作为 stdio MCP 服务被 agent 调用，工具自动从 `mcps/os/` 加载。
- **web**：进入 `web/`，执行 `yarn` 安装依赖，`yarn dev` 启动开发服务器（默认 `http://localhost:4100`），后端代理与 API 配置见 `web/README.md` 与 `web/.env.example`。

## 参与贡献

1. Fork 本仓库
2. 新建 `Feat_xxx` 分支
3. 提交代码
4. 新建 Pull Request
