from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    """Read a YAML file and ensure its top-level value is a mapping."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"expected mapping in yaml: {path}")
    return raw


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON file and ensure its top-level value is an object."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected object in json: {path}")
    return raw
