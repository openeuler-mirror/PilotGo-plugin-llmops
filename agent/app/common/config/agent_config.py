from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.common.file_readers import read_json_object, read_yaml_mapping


AGENTS_DIR = Path(__file__).resolve().parents[2] / "agent_orchestration" / "agents"


@dataclass(slots=True)
class AgentConfig:
    """Declarative config for one agent instance."""

    id: str
    name: str
    description: str | None = None
    model: str | None = None
    instructions: str | list[str] | None = None
    options: dict[str, Any] = field(default_factory=dict)
    build_mode: str = "agent"
    build_refs: list[str] = field(default_factory=list)
    build_options: dict[str, Any] = field(default_factory=dict)
    agent_key: str | None = None
    agent_dir: Path | None = None
    builder_file: Path | None = None
    optional_configs: dict[str, Any] = field(default_factory=dict)


def _optional_file_payloads(agent_dir: Path) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    # skill.yaml is intentionally not loaded; only skill.json / knowledge.yaml / knowledge.json / mcp.json are used.
    for filename in ("knowledge.yaml", "knowledge.json"):
        path = agent_dir / filename
        if path.exists():
            if path.suffix == ".yaml":
                payloads[filename] = read_yaml_mapping(path)
            else:
                payloads[filename] = read_json_object(path)

    skill_json = agent_dir / "skill.json"
    if skill_json.exists():
        payloads["skill.json"] = read_json_object(skill_json)

    mcp_path = agent_dir / "mcp.json"
    if mcp_path.exists():
        payloads["mcp.json"] = read_json_object(mcp_path)
    return payloads


def _build_config(agent_dir: Path) -> AgentConfig:
    agent_yaml = agent_dir / "agent.yaml"
    agent_py = agent_dir / "agent.py"
    if not agent_yaml.exists():
        raise FileNotFoundError(f"missing required file: {agent_yaml}")
    if not agent_py.exists():
        raise FileNotFoundError(f"missing required file: {agent_py}")

    raw = read_yaml_mapping(agent_yaml)
    name = raw.get("name")
    agent_id = raw.get("id")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"field 'name' must be a non-empty string in {agent_yaml}")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError(f"field 'id' must be a non-empty string in {agent_yaml}")

    options = raw.get("options", {})
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise ValueError(f"field 'options' must be object in {agent_yaml}")

    build = raw.get("build", {})
    if build is None:
        build = {}
    if not isinstance(build, dict):
        raise ValueError(f"field 'build' must be object in {agent_yaml}")

    build_mode_raw = build.get("mode", "agent")
    if not isinstance(build_mode_raw, str):
        raise ValueError(f"field 'build.mode' must be string in {agent_yaml}")
    build_mode = build_mode_raw.strip().lower() or "agent"
    if build_mode not in {"agent", "team", "workflow"}:
        raise ValueError(
            f"field 'build.mode' must be one of agent/team/workflow in {agent_yaml}"
        )

    build_refs = build.get("refs", [])
    if build_refs is None:
        build_refs = []
    if not isinstance(build_refs, list) or not all(isinstance(x, str) for x in build_refs):
        raise ValueError(f"field 'build.refs' must be list[str] in {agent_yaml}")

    build_options = build.get("options", {})
    if build_options is None:
        build_options = {}
    if not isinstance(build_options, dict):
        raise ValueError(f"field 'build.options' must be object in {agent_yaml}")

    instructions = raw.get("instructions")
    if instructions is not None and not isinstance(instructions, (str, list)):
        raise ValueError(f"field 'instructions' must be str or list[str] in {agent_yaml}")
    if isinstance(instructions, list) and not all(isinstance(x, str) for x in instructions):
        raise ValueError(f"field 'instructions' must be str or list[str] in {agent_yaml}")

    optional_configs = _optional_file_payloads(agent_dir)

    return AgentConfig(
        id=agent_id.strip(),
        name=name.strip(),
        description=raw.get("description"),
        model=raw.get("model"),
        instructions=instructions,
        options=options,
        build_mode=build_mode,
        build_refs=[x.strip() for x in build_refs if x.strip()],
        build_options=build_options,
        agent_key=agent_dir.name,
        agent_dir=agent_dir,
        builder_file=agent_py,
        optional_configs=optional_configs,
    )


def list_agent_configs() -> list[AgentConfig]:
    if not AGENTS_DIR.exists():
        raise FileNotFoundError(f"agents directory not found: {AGENTS_DIR}")

    configs: list[AgentConfig] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for agent_dir in sorted(p for p in AGENTS_DIR.iterdir() if p.is_dir()):
        config = _build_config(agent_dir)
        if config.id in seen_ids:
            raise ValueError(f"duplicate agent id: {config.id}")
        if config.name in seen_names:
            raise ValueError(f"duplicate agent name: {config.name}")
        seen_ids.add(config.id)
        seen_names.add(config.name)
        configs.append(config)

    if not configs:
        raise ValueError(f"no agent definitions found under {AGENTS_DIR}")
    return configs
