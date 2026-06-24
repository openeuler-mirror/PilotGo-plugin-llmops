from __future__ import annotations

from pathlib import Path
from typing import Any

from app.common.config.agent_config import AgentConfig
from app.common.errors import KnowledgeConfigError


def _resolve_under_agent_dir(raw_path: str, agent_dir: Path) -> Path:
    p = Path(raw_path).expanduser()
    return p.resolve() if p.is_absolute() else (agent_dir / p).resolve()


def _skill_json_bundle_paths(data: dict[str, Any], agent_dir: Path) -> list[Path]:
    raw_skills = data.get("skills")
    if not isinstance(raw_skills, dict) or not raw_skills:
        return []
    paths: list[Path] = []
    for alias, cfg in raw_skills.items():
        if not isinstance(alias, str) or not alias.strip():
            continue
        if not isinstance(cfg, dict):
            continue
        p = cfg.get("path")
        if not isinstance(p, str) or not p.strip():
            continue
        paths.append(_resolve_under_agent_dir(p, agent_dir))
    return paths


def load_skill_config(
    kwargs: dict[str, Any],
    config: AgentConfig,
) -> None:
    """Merge skill.json into kwargs."""
    raw_json = config.optional_configs.get("skill.json")
    if isinstance(raw_json, dict):
        if config.agent_dir:
            from agno.skills import LocalSkills, Skills

            loaders = [
                LocalSkills(str(bundle_path), validate=True)
                for bundle_path in _skill_json_bundle_paths(raw_json, config.agent_dir)
            ]
            if loaders:
                kwargs["skills"] = Skills(loaders)


def load_knowledge_config(kwargs: dict[str, Any], config: AgentConfig) -> None:
    raw_json = config.optional_configs.get("knowledge.json")
    if not isinstance(raw_json, dict):
        return

    kb_map = raw_json.get("knowledgeBases")
    if not isinstance(kb_map, dict) or not kb_map:
        return

    # Support loading exactly one knowledge base from knowledge.json by default.
    if len(kb_map) != 1:
        raise KnowledgeConfigError(
            f"Expected exactly 1 knowledge base in knowledge.json, but got {len(kb_map)}. "
            f"Currently only single knowledge base configuration is supported."
        )

    kb_name, kb_cfg = next(iter(kb_map.items()))
    if not isinstance(kb_name, str) or not kb_name.strip() or not isinstance(kb_cfg, dict):
        return

    kb_type = kb_cfg.get("type")
    if not isinstance(kb_type, str):
        return
    kb_type = kb_type.strip().lower()

    from agno.knowledge.knowledge import Knowledge

    if kb_type == "stdio":
        collection = kb_cfg.get("collection")
        kb_path = kb_cfg.get("path")
        embedder_cfg = kb_cfg.get("embedder")
        if not isinstance(collection, str) or not collection.strip():
            return
        if not isinstance(kb_path, str) or not kb_path.strip():
            return
        if not isinstance(embedder_cfg, dict):
            return

        embedder_id = embedder_cfg.get("id")
        embedder_host = embedder_cfg.get("host")
        embedder_dims = embedder_cfg.get("dimensions")
        if not isinstance(embedder_id, str) or not embedder_id.strip():
            return
        if not isinstance(embedder_host, str) or not embedder_host.strip():
            return
        if not isinstance(embedder_dims, int) or embedder_dims <= 0:
            return

        from agno.knowledge.embedder.ollama import OllamaEmbedder
        from agno.vectordb.chroma import ChromaDb
        from agno.vectordb.search import SearchType

        kwargs["knowledge"] = Knowledge(
            name=kb_name.strip(),
            vector_db=ChromaDb(
                collection=collection.strip(),
                path=kb_path.strip(),
                persistent_client=True,
                search_type=SearchType.hybrid,
                embedder=OllamaEmbedder(
                    id=embedder_id.strip(),
                    host=embedder_host.strip(),
                    dimensions=embedder_dims,
                ),
            ),
            max_results=3,
        )
        return

    if kb_type == "http":
        base_url = kb_cfg.get("base_url")
        api_key = kb_cfg.get("api_key")
        search_id = kb_cfg.get("search_id")
        kb_id = kb_cfg.get("kb_id")

        if not isinstance(base_url, str) or not base_url.strip():
            return
        if not isinstance(api_key, str) or not api_key.strip():
            return
        if not isinstance(search_id, str) or not search_id.strip():
            return
        if not isinstance(kb_id, str) or not kb_id.strip():
            return

        from app.common.vectordb_adapter.ragflow_vectordb import RagFlowVectorDb

        kwargs["knowledge"] = Knowledge(
            name=kb_name.strip(),
            vector_db=RagFlowVectorDb(
                base_url=base_url.strip(),
                api_key=api_key.strip(),
                search_id=search_id.strip(),
                kb_id=kb_id.strip(),
                timeout=30,
            ),
            max_results=3,
        )


def load_mcp_config(kwargs: dict[str, Any], config: AgentConfig) -> None:
    """Merge mcp.json into kwargs as MCPTools under `tools`."""
    raw = config.optional_configs.get("mcp.json")
    if not isinstance(raw, dict):
        return
    if config.agent_dir is None:
        return

    mcp_servers = raw.get("mcpServers", {})
    if not isinstance(mcp_servers, dict) or not mcp_servers:
        return

    from agno.tools.mcp import MCPTools
    from agno.tools.mcp.params import SSEClientParams, StreamableHTTPClientParams
    from mcp.client.stdio import StdioServerParameters

    def _normalize_transport(server_cfg: dict[str, Any]) -> str:
        raw_transport = server_cfg.get("transport", server_cfg.get("type", "stdio"))
        if not isinstance(raw_transport, str) or not raw_transport.strip():
            return "stdio"
        val = raw_transport.strip().lower()
        if val == "stdio":
            return "stdio"
        if val == "sse":
            return "sse"
        if val in {"streamable_http", "streamable-http", "streamable"}:
            return "streamable-http"
        return val

    def _coerce_headers(raw_headers: Any) -> dict[str, Any] | None:
        if raw_headers is None:
            return None
        if not isinstance(raw_headers, dict):
            return None
        headers: dict[str, Any] = {}
        for k, v in raw_headers.items():
            if not isinstance(k, str) or not k.strip():
                continue
            headers[k] = v
        return headers or None

    toolkits: list[Any] = []
    for server_name, server_cfg in mcp_servers.items():
        if not isinstance(server_name, str) or not server_name.strip():
            continue
        if not isinstance(server_cfg, dict):
            continue

        transport = _normalize_transport(server_cfg)

        if transport == "stdio":
            command = server_cfg.get("command")
            args = server_cfg.get("args", [])
            if not isinstance(command, str) or not command.strip():
                continue
            if args is None:
                args = []
            if not isinstance(args, list) or not all(isinstance(x, str) for x in args):
                continue

            env = server_cfg.get("env")
            if env is not None and not isinstance(env, dict):
                env = None
            if isinstance(env, dict) and not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
                env = None

            cwd = server_cfg.get("cwd")
            if isinstance(cwd, str) and cwd.strip():
                cwd_path = _resolve_under_agent_dir(cwd, config.agent_dir)
                cwd_val: str | Path = cwd_path
            else:
                cwd_val = None

            server_params = StdioServerParameters(command=command, args=list(args), env=env, cwd=cwd_val)
            toolkits.append(
                MCPTools(
                    server_params=server_params,
                    transport="stdio",
                    tool_name_prefix=server_name.strip(),
                )
            )
            continue

        if transport in {"sse", "streamable-http"}:
            url = server_cfg.get("url")
            if not isinstance(url, str) or not url.strip():
                continue

            headers = _coerce_headers(server_cfg.get("headers"))

            timeout_raw = server_cfg.get("timeout", server_cfg.get("http_timeout"))
            sse_read_timeout_raw = server_cfg.get("sse_read_timeout")

            if transport == "sse":
                # agno MCPTools: min(self.timeout_seconds, sse_params.get("timeout", ...)) —
                # asdict() keeps explicit None keys, so .get returns None and min() raises.
                # Omit None by always passing numeric defaults (match SSEClientParams).
                sse_timeout = float(timeout_raw) if isinstance(timeout_raw, (int, float)) else 5.0
                sse_read = (
                    float(sse_read_timeout_raw) if isinstance(sse_read_timeout_raw, (int, float)) else float(60 * 5)
                )
                server_params = SSEClientParams(
                    url=url.strip(),
                    headers=headers,
                    timeout=sse_timeout,
                    sse_read_timeout=sse_read,
                )
            else:
                from datetime import timedelta

                timeout: float | None
                if isinstance(timeout_raw, (int, float)):
                    timeout = float(timeout_raw)
                else:
                    timeout = None
                sse_read_timeout: float | None
                if isinstance(sse_read_timeout_raw, (int, float)):
                    sse_read_timeout = float(sse_read_timeout_raw)
                else:
                    sse_read_timeout = None

                td_timeout = timedelta(seconds=timeout) if timeout is not None else None
                td_read_timeout = timedelta(seconds=sse_read_timeout) if sse_read_timeout is not None else None

                params_kwargs: dict[str, Any] = {"url": url.strip(), "headers": headers}
                if td_timeout is not None:
                    params_kwargs["timeout"] = td_timeout
                if td_read_timeout is not None:
                    params_kwargs["sse_read_timeout"] = td_read_timeout
                terminate_on_close = server_cfg.get("terminate_on_close")
                if isinstance(terminate_on_close, bool):
                    params_kwargs["terminate_on_close"] = terminate_on_close

                server_params = StreamableHTTPClientParams(**params_kwargs)

            toolkits.append(
                MCPTools(
                    server_params=server_params,
                    transport=transport,
                    tool_name_prefix=server_name.strip(),
                )
            )
            continue

    if not toolkits:
        return

    existing_tools = kwargs.get("tools")
    if existing_tools is None:
        kwargs["tools"] = toolkits
        return
    if isinstance(existing_tools, list):
        existing_tools.extend(toolkits)
        kwargs["tools"] = existing_tools
        return

