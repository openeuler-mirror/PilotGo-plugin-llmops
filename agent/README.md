# PilotGo LLM Agent

基于 [Agno](https://github.com/agno-agi/agno) 框架的 LLM Agent 模块，为 PilotGo 插件提供大模型驱动的智能体能力。项目涵盖 Agent 构建、多智能体协作（Team）、工作流编排（Workflow），以及自定义工具与 MCP（Model Context Protocol）集成等能力。

当前代码以**可运行示例与开发脚手架**为主，便于在此基础上扩展集群故障分析、巡检与运维等业务能力。

## 功能概览

| 模块 | 说明 |
|------|------|
| **Agent** | 通用对话 Agent、结构化输出 Agent |
| **Team** | 多 Agent 协作，分工研究与总结 |
| **Workflow** | 多步骤流水线编排，支持流式事件输出 |
| **Tools** | 自定义 Shell 命令工具，支持执行前人工确认 |
| **MCP** | 接入外部 MCP 服务（Agno 文档、GitHub 等） |

## 环境要求

- Python **3.11+**
- 可访问的 **OpenAI 兼容 LLM API**（模型名、Base URL、API Key）
- 推荐使用 [uv](https://github.com/astral-sh/uv) 管理依赖
- 运行 MCP GitHub 示例时需安装 **Node.js**（用于 `npx`）

## 快速开始

### 1. 安装依赖

```bash
cd agent
uv sync
```

若未安装 uv，可使用 pip：

```bash
pip install agno fastapi openai pyyaml rich mcp
```

### 2. 配置 LLM

编辑 `config.yaml`，填入 LLM 连接信息：

```yaml
llm:
  id: "your-model-name"      # 模型名称，如 gpt-4o、qwen-plus
  base_url: "https://..."    # OpenAI 兼容 API 地址
  api_key: "sk-..."          # API Key
```

### 3. 运行示例

在 `agent/` 目录下执行：

```bash
# 简单 Agent 对话（流式 + 非流式）
uv run python -m src.agents.run

# AI 趋势内容规划工作流
uv run python -m src.workflows.ai_trend

# 带人工确认机制的 Shell 工具 Agent
uv run python -m src.tools.tool_confirm

# MCP 集成示例（需网络；GitHub 示例需 npx）
uv run python -m src.tools.tool_mcp
```

## 项目结构

```
agent/
├── config.yaml              # LLM 配置
├── main.py                  # 占位入口（待扩展）
├── pyproject.toml           # 项目依赖定义
├── src/
│   ├── config/
│   │   └── configs.py       # 配置加载（YAML / JSON）
│   ├── agents/
│   │   ├── build.py         # Agent 工厂函数
│   │   └── run.py           # Agent 运行示例
│   ├── workflows/
│   │   └── ai_trend.py      # 多 Agent 工作流示例
│   └── tools/
│       ├── common.py        # Shell 命令工具定义
│       ├── tool_confirm.py  # Human-in-the-loop 示例
│       └── tool_mcp.py      # MCP 集成示例
└── README.md
```

## 模块说明

### Agent 构建（`src/agents/`）

- `build.py`：提供 `create_agent()` 与 `create_schema_agent()`，分别用于通用对话和结构化输出场景。
- `run.py`：演示同步/异步调用 Agent，支持流式响应。

### 工作流（`src/workflows/ai_trend.py`）

演示完整的多步骤内容规划流程：

```
输入主题 → Research Team（研究 + 总结）→ Content Planner（4 周内容规划）→ 输出汇总
```

默认输入为 `"2025 年 AI 趋势"`，运行时会以流式事件打印各步骤进度。

### 工具（`src/tools/`）

- **common.py**：定义 `run_shell_command` 工具，执行 Shell 命令并返回输出；标记为 `requires_confirmation=True`，执行前需用户确认。
- **tool_confirm.py**：演示 Human-in-the-loop 流程——Agent 暂停运行，等待用户确认后再继续执行敏感操作。
- **tool_mcp.py**：演示通过 MCP 连接外部服务，包含 Agno 文档 MCP（HTTP）与 GitHub MCP（Stdio）两个示例。

### 配置（`src/config/configs.py`）

从 `agent/config.yaml` 读取 LLM 配置，支持 YAML 与 JSON 格式。各模块通过 `get_llm_config()` 获取统一配置。

## 依赖说明

| 包 | 用途 |
|----|------|
| `agno` | Agent / Team / Workflow 框架 |
| `openai` | OpenAI 兼容 API 客户端 |
| `mcp` | Model Context Protocol 客户端 |
| `fastapi` | 预留 Web 服务依赖（尚未接入） |

## 开发状态

| 能力 | 状态 |
|------|------|
| Agent / Team / Workflow 示例 | ✅ 可用 |
| 自定义工具 / MCP 集成 | ✅ 可用 |
| 统一 CLI 入口 | 🔲 `main.py` 为占位实现 |
| HTTP API 服务 | 🔲 FastAPI 已声明依赖，尚未实现 |

## 常见问题

**Q: 运行时提示找不到 `src` 模块？**

请在 `agent/` 目录下执行命令，并使用 `python -m src.xxx` 方式运行，确保包路径正确。

**Q: MCP 示例运行失败？**

- Agno 文档 MCP 需要可访问 `https://docs.agno.com/mcp` 的网络环境。
- GitHub MCP 需要本地安装 Node.js，并通过 `npx` 拉取 `@modelcontextprotocol/server-github`。

**Q: LLM 调用报错？**

请检查 `config.yaml` 中的 `id`、`base_url`、`api_key` 是否正确，以及 API 服务是否可达。
