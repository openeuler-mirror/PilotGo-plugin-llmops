from __future__ import annotations

from collections import deque
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Callable, Iterable

from app.common.config.agent_config import AgentConfig

AgentBuilder = Callable[[AgentConfig, list[Any] | None], Any]
_BUILDER_CACHE: dict[Path, AgentBuilder] = {}


def get_team_class() -> type:
    """Lazy import for team builds (keeps import cost low for agent-only apps)."""
    from agno.team import Team

    return Team


def get_workflow_types() -> tuple[type, type]:
    """Return (Workflow, Step) for workflow builds."""
    from agno.workflow import Workflow
    from agno.workflow.step import Step

    return Workflow, Step


def _load_agent_builder(builder_file: Path) -> AgentBuilder:
    cached = _BUILDER_CACHE.get(builder_file)
    if cached is not None:
        return cached

    if not builder_file.exists():
        raise FileNotFoundError(f"agent builder file not found: {builder_file}")

    module_name = f"agent_builder_{builder_file.parent.name}_{abs(hash(builder_file))}"
    spec = spec_from_file_location(module_name, builder_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import agent builder module: {builder_file}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    build_fn = getattr(module, "build", None)
    if not callable(build_fn):
        raise AttributeError(f"missing callable 'build(config, refs)' in {builder_file}")

    _BUILDER_CACHE[builder_file] = build_fn
    return build_fn


def _build_by_agent_file(config: AgentConfig, refs: list[Any]) -> Any:
    if config.builder_file is None:
        raise ValueError(f"builder_file is required for agent '{config.name}'")
    builder = _load_agent_builder(config.builder_file)
    return builder(config, refs)


def build_agent(
    config: AgentConfig,
    refs: list[Any] | None = None,
) -> Any:
    """Build one runtime object using each agent's own builder file."""
    refs = refs or []
    if config.builder_file is None:
        raise ValueError(f"builder_file is required for agent '{config.name}'")
    return _build_by_agent_file(config, refs)


def _resolve_build(
    target_name: str,
    config_map: dict[str, AgentConfig],
    built: dict[str, Any],
    stack: set[str],
) -> Any:
    if target_name in built:
        return built[target_name]
    if target_name in stack:
        raise ValueError(f"circular build dependency detected at '{target_name}'")
    config = config_map.get(target_name)
    if config is None:
        raise ValueError(f"agent reference '{target_name}' not found")

    stack.add(target_name)
    resolved_refs = [
        _resolve_build(ref_name, config_map, built, stack) for ref_name in config.build_refs
    ]
    obj = build_agent(config, refs=resolved_refs)
    stack.remove(target_name)
    built[target_name] = obj
    return obj


def _topo_build_order(config_map: dict[str, AgentConfig]) -> list[str]:
    """Dependency-first order: leaves (no refs) before composites that reference them."""
    in_degree: dict[str, int] = {name: 0 for name in config_map}
    dependents: dict[str, list[str]] = {name: [] for name in config_map}
    for name, cfg in config_map.items():
        for ref in cfg.build_refs:
            if ref not in config_map:
                raise ValueError(
                    f"agent '{name}' build.refs references unknown agent '{ref}'"
                )
            dependents[ref].append(name)
            in_degree[name] += 1

    queue = deque(sorted(n for n, deg in in_degree.items() if deg == 0))
    ordered: list[str] = []
    while queue:
        n = queue.popleft()
        ordered.append(n)
        for child in sorted(dependents[n]):
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    if len(ordered) != len(config_map):
        raise ValueError("circular build.refs in agent.yaml (composite agents)")
    return ordered


def build_agents(configs: Iterable[AgentConfig]) -> list[Any]:
    config_map = {config.name: config for config in configs}
    built: dict[str, Any] = {}
    order = _topo_build_order(config_map)
    for name in order:
        _resolve_build(name, config_map, built, set())
    return [built[name] for name in order]
