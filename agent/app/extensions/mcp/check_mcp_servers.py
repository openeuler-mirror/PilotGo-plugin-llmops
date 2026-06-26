#!/usr/bin/env python3
"""Check MCP server count, tool count, and connectivity from mcp.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"mcp config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"mcp config must be a JSON object: {path}")
    return payload


def _server_transport(server_config: dict[str, Any]) -> str:
    """
    Return normalized transport string for a server config.

    Supported:
    - stdio (default)
    - sse
    - streamable_http (aka streamable-http / streamable)
    """
    raw = server_config.get("transport", server_config.get("type", "stdio"))
    if not isinstance(raw, str) or not raw.strip():
        return "stdio"
    val = raw.strip().lower()
    if val in {"stdio"}:
        return "stdio"
    if val in {"sse"}:
        return "sse"
    if val in {"streamable_http", "streamable-http", "streamable"}:
        return "streamable_http"
    return val


def _send_jsonrpc(proc: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if proc.stdin is None:
        raise RuntimeError("stdin is not available for MCP server process")
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()


def _recv_jsonrpc(proc: subprocess.Popen[str]) -> dict[str, Any]:
    if proc.stdout is None:
        raise RuntimeError("stdout is not available for MCP server process")
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("empty response from MCP server")
    try:
        payload = json.loads(line.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON response: {line.strip()}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("response must be a JSON object")
    return payload


def _parse_server_command(server_name: str, server_config: dict[str, Any]) -> list[str]:
    transport = _server_transport(server_config)
    if transport != "stdio":
        raise ValueError(f"server '{server_name}' unsupported transport for command: {transport}")

    command = server_config.get("command")
    args = server_config.get("args", [])
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f"server '{server_name}' missing non-empty 'command'")
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise ValueError(f"server '{server_name}' field 'args' must be list[str]")
    return [command, *args]


def _check_stdio_server(server_name: str, server_config: dict[str, Any], terminate_timeout: int) -> dict[str, Any]:
    try:
        command = _parse_server_command(server_name, server_config)
    except Exception as exc:
        return {"connected": False, "tool_count": 0, "error": str(exc)}

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        _send_jsonrpc(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-checker", "version": "1.0.0"},
                },
            },
        )
        init_resp = _recv_jsonrpc(process)
        if "error" in init_resp:
            return {"connected": False, "tool_count": 0, "error": f"initialize failed: {init_resp['error']}"}

        _send_jsonrpc(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send_jsonrpc(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = _recv_jsonrpc(process)
        if "error" in tools_resp:
            return {"connected": False, "tool_count": 0, "error": f"tools/list failed: {tools_resp['error']}"}

        tools = tools_resp.get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            return {"connected": False, "tool_count": 0, "error": "invalid tools/list result shape"}
        return {"connected": True, "tool_count": len(tools), "error": ""}

    except Exception as exc:
        return {"connected": False, "tool_count": 0, "error": str(exc)}
    finally:
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=terminate_timeout)
            except Exception:
                process.kill()


def _redact_headers(headers: dict[str, Any] | None) -> dict[str, Any] | None:
    if not headers:
        return headers
    safe: dict[str, Any] = {}
    for k, v in headers.items():
        if isinstance(k, str) and k.lower() in {"authorization", "proxy-authorization", "x-api-key"}:
            safe[k] = "***redacted***"
        else:
            safe[k] = v
    return safe


def _check_http_server(
    *,
    transport: str,
    server_name: str,
    server_config: dict[str, Any],
    http_timeout: float,
    sse_read_timeout: float,
) -> dict[str, Any]:
    url = server_config.get("url")
    if not isinstance(url, str) or not url.strip():
        return {"connected": False, "tool_count": 0, "error": f"server '{server_name}' missing non-empty 'url'"}

    headers = server_config.get("headers")
    if headers is not None and not isinstance(headers, dict):
        return {"connected": False, "tool_count": 0, "error": f"server '{server_name}' field 'headers' must be object"}
    if isinstance(headers, dict) and not all(isinstance(k, str) for k in headers.keys()):
        return {"connected": False, "tool_count": 0, "error": f"server '{server_name}' field 'headers' keys must be strings"}

    async def _run() -> tuple[bool, int, str]:
        try:
            import anyio
            import httpx
            from mcp.client.session import ClientSession

            if transport == "sse":
                from mcp.client.sse import sse_client

                async with sse_client(
                    url,
                    headers=headers,
                    timeout=float(http_timeout),
                    sse_read_timeout=float(sse_read_timeout),
                ) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        return True, len(tools.tools), ""

            if transport == "streamable_http":
                from mcp.client.streamable_http import streamable_http_client

                timeout = httpx.Timeout(float(http_timeout), read=float(sse_read_timeout))
                async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
                    async with streamable_http_client(url, http_client=client) as (read_stream, write_stream, _get_sid):
                        async with ClientSession(read_stream, write_stream) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            return True, len(tools.tools), ""

            return False, 0, f"unsupported transport: {transport}"
        except ImportError as exc:
            # Most common cause: running with system python instead of project .venv
            return (
                False,
                0,
                f"missing dependency for {transport} transport: {exc}. "
                f"Tip: run with project's venv python (e.g. .venv/bin/python).",
            )
        except Exception as exc:
            return False, 0, str(exc)

    try:
        import anyio  # type: ignore[import-not-found]

        connected, tool_count, err = anyio.run(_run)
        if not connected and not err:
            err = f"connection failed (transport={transport}, url={url}, headers={_redact_headers(headers)})"
        return {"connected": connected, "tool_count": int(tool_count), "error": err}
    except ImportError as exc:
        return {
            "connected": False,
            "tool_count": 0,
            "error": f"missing dependency for async runner: {exc}. Tip: run with project's venv python.",
        }


def _check_server(
    server_name: str,
    server_config: dict[str, Any],
    *,
    terminate_timeout: int,
    http_timeout: float,
    sse_read_timeout: float,
) -> dict[str, Any]:
    transport = _server_transport(server_config)
    if transport == "stdio":
        return _check_stdio_server(server_name, server_config, terminate_timeout=terminate_timeout)
    if transport in {"sse", "streamable_http"}:
        return _check_http_server(
            transport=transport,
            server_name=server_name,
            server_config=server_config,
            http_timeout=http_timeout,
            sse_read_timeout=sse_read_timeout,
        )
    return {"connected": False, "tool_count": 0, "error": f"server '{server_name}' unsupported transport: {transport}"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check MCP server count, tool count, and connectivity from mcp.json."
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent / "mcp.json"),
        help="Path to mcp.json (default: app/extensions/mcp/mcp.json)",
    )
    parser.add_argument(
        "--terminate-timeout",
        type=int,
        default=5,
        help="Timeout seconds when terminating test process (default: 5)",
    )
    parser.add_argument(
        "--http-timeout",
        type=float,
        default=10.0,
        help="HTTP connect/write timeout seconds for SSE/streamable transports (default: 10)",
    )
    parser.add_argument(
        "--sse-read-timeout",
        type=float,
        default=60.0,
        help="SSE read timeout seconds for SSE/streamable transports (default: 60)",
    )
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    config = _read_config(config_path)
    mcp_servers = config.get("mcpServers", {})
    if not isinstance(mcp_servers, dict):
        raise ValueError("field 'mcpServers' must be an object")

    print(f"Config: {config_path}")
    print(f"MCP server count: {len(mcp_servers)}")
    print("-" * 72)

    if not mcp_servers:
        print("No MCP servers configured.")
        return 0

    connected_count = 0
    for server_name, server_config in mcp_servers.items():
        if not isinstance(server_config, dict):
            result = {"connected": False, "tool_count": 0, "error": "server config must be object"}
        else:
            result = _check_server(
                server_name,
                server_config,
                terminate_timeout=args.terminate_timeout,
                http_timeout=args.http_timeout,
                sse_read_timeout=args.sse_read_timeout,
            )

        status = "OK" if result["connected"] else "FAIL"
        if result["connected"]:
            connected_count += 1
        print(f"[{status}] {server_name}")
        print(f"  tools: {result['tool_count']}")
        print(f"  connected: {result['connected']}")
        if result["error"]:
            print(f"  error: {result['error']}")
        print("-" * 72)

    print(f"Connected: {connected_count}/{len(mcp_servers)}")
    return 0 if connected_count == len(mcp_servers) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise SystemExit(2)
