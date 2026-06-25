#!/usr/bin/env python3
"""Knowledge base health checker.

Usage:
  python app/extensions/knowledge/kb_health_check.py
  python app/extensions/knowledge/kb_health_check.py --skip-network
  python app/extensions/knowledge/kb_health_check.py --config /path/to/knowledge.json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    kb_type: str
    score: int = 100
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)

    def add_error(self, msg: str, penalty: int = 20) -> None:
        self.errors.append(msg)
        self.score = max(0, self.score - penalty)

    def add_warning(self, msg: str, penalty: int = 10) -> None:
        self.warnings.append(msg)
        self.score = max(0, self.score - penalty)

    def add_detail(self, msg: str) -> None:
        self.details.append(msg)

    @property
    def status(self) -> str:
        if self.errors:
            return "UNHEALTHY"
        if self.warnings:
            return "DEGRADED"
        return "HEALTHY"


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("knowledge.json root should be a JSON object")
    return data


def check_http_endpoint(url: str, timeout: int) -> tuple[bool, str]:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False, "invalid URL format"

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if host is None:
        return False, "invalid host in URL"

    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except OSError as exc:
        return False, f"socket check failed: {exc}"

    try:
        req = Request(url, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
            if 200 <= int(code) < 500:
                return True, f"HTTP {code}"
            return False, f"HTTP {code}"
    except Exception as exc:  # noqa: BLE001 - best effort probe
        return False, f"http probe failed: {exc}"


def check_stdio_kb(name: str, cfg: dict[str, Any]) -> CheckResult:
    result = CheckResult(name=name, kb_type="stdio")

    required_fields = ("collection", "path")
    for f in required_fields:
        if not cfg.get(f):
            result.add_error(f"missing required field: {f}", penalty=25)

    kb_path = cfg.get("path")
    if kb_path:
        path = Path(kb_path)
        if not path.exists():
            result.add_error(f"path does not exist: {path}", penalty=30)
        elif not path.is_dir():
            result.add_error(f"path is not a directory: {path}", penalty=30)
        else:
            result.add_detail(f"path exists: {path}")
            sqlite = path / "chroma.sqlite3"
            if sqlite.exists():
                size_mb = sqlite.stat().st_size / (1024 * 1024)
                result.add_detail(f"chroma.sqlite3 present: {size_mb:.2f} MB")
            else:
                result.add_warning("missing chroma.sqlite3", penalty=15)

            bin_count = len(list(path.glob("**/*.bin")))
            if bin_count == 0:
                result.add_warning("no .bin index files found", penalty=15)
            else:
                result.add_detail(f"index files found: {bin_count}")

            if os.access(path, os.R_OK | os.X_OK):
                result.add_detail("directory is readable")
            else:
                result.add_error("directory is not readable", penalty=20)

    embedder = cfg.get("embedder", {})
    if not isinstance(embedder, dict):
        result.add_error("embedder must be an object", penalty=20)
        return result

    if not embedder.get("id"):
        result.add_warning("embedder.id is empty", penalty=10)

    host = embedder.get("host")
    if not host:
        result.add_warning("embedder.host is empty", penalty=10)

    dimensions = embedder.get("dimensions")
    if not isinstance(dimensions, int) or dimensions <= 0:
        result.add_warning("embedder.dimensions should be a positive integer", penalty=10)

    return result


def check_http_kb(name: str, cfg: dict[str, Any], skip_network: bool, timeout: int) -> CheckResult:
    result = CheckResult(name=name, kb_type="http")

    required_fields = ("base_url", "api_key", "search_id", "kb_id")
    for f in required_fields:
        if not cfg.get(f):
            result.add_error(f"missing required field: {f}", penalty=20)

    base_url = cfg.get("base_url")
    if base_url and not skip_network:
        ok, detail = check_http_endpoint(base_url, timeout=timeout)
        if ok:
            result.add_detail(f"endpoint check passed: {detail}")
        else:
            result.add_warning(f"endpoint check failed: {detail}", penalty=20)
    elif skip_network:
        result.add_detail("network check skipped by --skip-network")

    return result


def check_knowledge_bases(config: dict[str, Any], skip_network: bool, timeout: int) -> list[CheckResult]:
    kb_map = config.get("knowledgeBases")
    if not isinstance(kb_map, dict) or not kb_map:
        raise ValueError("knowledgeBases must be a non-empty object")

    results: list[CheckResult] = []
    for name, cfg in kb_map.items():
        if not isinstance(cfg, dict):
            r = CheckResult(name=name, kb_type="unknown")
            r.add_error("invalid config type, expected object", penalty=40)
            results.append(r)
            continue

        kb_type = cfg.get("type")
        if kb_type == "stdio":
            results.append(check_stdio_kb(name=name, cfg=cfg))
        elif kb_type == "http":
            results.append(check_http_kb(name=name, cfg=cfg, skip_network=skip_network, timeout=timeout))
        else:
            r = CheckResult(name=name, kb_type=str(kb_type))
            r.add_error(f"unsupported kb type: {kb_type}", penalty=40)
            results.append(r)

    return results


def print_report(results: list[CheckResult]) -> int:
    print("=" * 72)
    print("Knowledge Base Health Report")
    print("=" * 72)

    for r in results:
        print(f"[{r.status:<9}] {r.name} (type={r.kb_type}) score={r.score}/100")
        for d in r.details:
            print(f"  - detail : {d}")
        for w in r.warnings:
            print(f"  - warning: {w}")
        for e in r.errors:
            print(f"  - error  : {e}")
        print("-" * 72)

    total = len(results)
    avg = sum(r.score for r in results) / total if total else 0
    unhealthy = sum(1 for r in results if r.status == "UNHEALTHY")
    degraded = sum(1 for r in results if r.status == "DEGRADED")
    healthy = total - unhealthy - degraded

    print("Summary")
    print(f"  - total      : {total}")
    print(f"  - healthy    : {healthy}")
    print(f"  - degraded   : {degraded}")
    print(f"  - unhealthy  : {unhealthy}")
    print(f"  - avg score  : {avg:.1f}/100")

    # Exit code: 0 healthy, 1 degraded only, 2 unhealthy exists
    if unhealthy > 0:
        return 2
    if degraded > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check health of configured knowledge bases.")
    default_config = Path(__file__).with_name("knowledge.json")
    parser.add_argument("--config", type=Path, default=default_config, help="Path to knowledge.json")
    parser.add_argument("--skip-network", action="store_true", help="Skip HTTP endpoint probing")
    parser.add_argument("--timeout", type=int, default=3, help="Network timeout in seconds")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        results = check_knowledge_bases(config, skip_network=args.skip_network, timeout=args.timeout)
    except Exception as exc:  # noqa: BLE001 - CLI should print full failure
        print(f"Health check failed to start: {exc}")
        return 2

    return print_report(results)


if __name__ == "__main__":
    raise SystemExit(main())
