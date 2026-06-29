# PilotGo-plugin-llmops · Web

PilotGo-plugin-llmops 的前端,LLM 辅助的集群故障分析、巡检与运维管理插件的 Web 控制台。

## 技术栈

- Vue 3 + TypeScript + Vite
- Element Plus(UI 组件)
- Pinia(状态管理)
- Vue Router
- ECharts / @antv/g6(图表与拓扑可视化)
- Tailwind CSS

## 环境要求

- Node.js `^20.19.0` 或 `>=22.12.0`

## 快速开始

```bash
# 安装依赖
yarn

# 启动开发服务器(默认 http://localhost:4100)
yarn dev

# 生产构建(含类型检查)
yarn build

# 预览构建产物
yarn preview
```

## 常用脚本

| 命令 | 说明 |
| --- | --- |
| `yarn dev` | 启动 Vite 开发服务器 |
| `yarn build` | 类型检查 + 生产构建 |
| `yarn preview` | 预览构建产物 |
| `yarn type-check` | 仅运行类型检查(vue-tsc) |
| `yarn lint` | ESLint 检查 |
| `yarn format` | Prettier 格式化 src/ |

## 后端代理配置

开发环境通过 Vite proxy 将 `/api` 转发到后端服务。相关环境变量见 `.env.example`:

- `VITE_API_BASE_URL` — 留空表示同源相对 `/api`(经 dev proxy 转发);设为绝对 URL 则直连远端
- `VITE_DEV_PROXY_TARGET` — 后端地址,默认 `http://localhost:8090`

复制 `.env.example` 为 `.env.local` 后按需修改。

## 目录结构

