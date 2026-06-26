"""Check skill bundles listed in skill.json: JSON shape, paths, and Agno load."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

_DEFAULT_JSON = Path(__file__).resolve().parent / "skill.json"


def _resolve(raw: str, registry_dir: Path) -> Path:
    p = Path(raw).expanduser()
    return p.resolve() if p.is_absolute() else (registry_dir / p).resolve()


def _read_skills_map(skill_json: Path) -> tuple[dict[str, str] | None, str | None]:
    """Return (alias -> path, error_message)."""
    try:
        data = json.loads(skill_json.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"file not found: {skill_json}"
    except json.JSONDecodeError as e:
        return None, f"invalid JSON: {e}"

    if not isinstance(data, dict):
        return None, "root must be a JSON object"
    raw_skills = data.get("skills")
    if not isinstance(raw_skills, dict) or not raw_skills:
        return None, "'skills' must be a non-empty object"

    out: dict[str, str] = {}
    for alias, cfg in raw_skills.items():
        if not isinstance(alias, str) or not alias.strip():
            return None, f"bad alias key: {alias!r}"
        if not isinstance(cfg, dict):
            return None, f"{alias!r}: value must be an object with 'path'"
        p = cfg.get("path")
        if not isinstance(p, str) or not p.strip():
            return None, f"{alias!r}: missing non-empty string 'path'"
        out[alias] = p
    return out, None


def _agno_load(bundle: Path) -> tuple[list[Any] | None, list[str]]:
    """Load with Agno (same as Agent). On failure returns (None, errors)."""
    try:
        from agno.skills import LocalSkills, SkillValidationError
    except ImportError:
        return None, ["cannot import agno (install project deps)"]

    try:
        skills = LocalSkills(str(bundle), validate=True).load()
    except SkillValidationError as e:
        return None, list(e.errors or [str(e)])
    except OSError as e:
        return None, [str(e)]
    except Exception as e:  # noqa: BLE001
        return None, [f"load failed: {e}"]

    if not skills:
        return None, [
            "no skills loaded — need SKILL.md on bundle root or in a non-hidden subfolder"
        ]
    return skills, []


def check_skill_registry(skill_json: Path) -> bool:
    """Print a report. Returns False if any entry failed (path or Agno load)."""
    skill_json = skill_json.resolve()
    base = skill_json.parent
    sep = "=" * 72
    sub = "-" * 72

    print(sep)
    print("skill.json 健康检查")
    print(f"配置: {skill_json}")
    print(sep)

    mapping, err = _read_skills_map(skill_json)
    if err:
        print(f"\n✗ 配置无效: {err}")
        print(sub)
        print("汇总")
        print("  检查项数: 0（配置未通过，未逐项检查）")
        print("  通过: 0 | 失败: 0 | 未加载 Agno: 0")
        print(sub)
        print("结果: 未通过")
        print(sep)
        return False

    try_agno = True
    try:
        import agno  # noqa: F401
    except ImportError:
        try_agno = False

    aliases_sorted = sorted(mapping)
    n_total = len(aliases_sorted)
    n_pass = 0
    n_fail = 0
    n_skip_agno = 0
    by_real_path: dict[Path, list[str]] = defaultdict(list)
    by_skill_name: dict[str, list[str]] = defaultdict(list)

    for i, alias in enumerate(aliases_sorted, start=1):
        raw = mapping[alias]
        path = _resolve(raw, base)
        by_real_path[path].append(alias)
        print(f"\n[{i}/{n_total}] {alias}")
        raw_p = Path(raw).expanduser()
        if raw_p.is_absolute():
            same_path = path == raw_p.resolve()
        else:
            same_path = path == (base / raw_p).resolve()
        if same_path:
            print(f"  资源包目录: {path}")
        else:
            print(f"  配置里写的路径: {raw}")
            print(f"  实际解析到的目录: {path}")

        if not path.exists():
            print("  状态: 失败 — 路径不存在")
            n_fail += 1
            continue
        if not path.is_dir():
            print("  状态: 失败 — 不是目录")
            n_fail += 1
            continue

        if not try_agno:
            print("  状态: 未验证 — 未安装 agno，仅确认路径存在")
            n_skip_agno += 1
            continue

        skills, errors = _agno_load(path)
        if errors:
            print("  状态: 失败 — Agno 无法加载")
            for msg in errors:
                print(f"    · {msg}")
            n_fail += 1
            continue

        names = [s.name for s in skills]
        print(f"  状态: 通过 — 已加载 {len(skills)} 个 skill: {', '.join(names)}")
        n_pass += 1
        for s in skills:
            by_skill_name[s.name].append(f"{alias} @ {path}")

    print()
    for p_item, alist in sorted(by_real_path.items(), key=lambda x: str(x[0])):
        if len(alist) > 1:
            print(f"提示: 多个别名指向同一目录: {', '.join(alist)}")
    for name, sources in sorted(by_skill_name.items()):
        if len(sources) > 1:
            print(
                f"提示: skill 名 {name!r} 在多条配置中出现（合并 Skills 时后者覆盖）: "
                f"{'；'.join(sources)}"
            )

    print(sub)
    print("汇总")
    print(f"  检查项数: {n_total}")
    chk_line = f"  通过: {n_pass} | 失败: {n_fail}"
    if n_skip_agno:
        chk_line += f" | 未执行 Agno 校验: {n_skip_agno}"
    print(chk_line)
    print(sub)
    if n_fail == 0 and n_skip_agno == 0:
        print("结果: 全部通过 ✓")
    elif n_fail == 0:
        print("结果: 无失败项，但有配置未做 Agno 加载（请安装依赖后重试）")
    else:
        print("结果: 存在失败项 ✗")
    print(sep)
    return n_fail == 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Health-check skill.json for Agno.")
    p.add_argument("skill_json", nargs="?", type=Path, default=_DEFAULT_JSON)
    args = p.parse_args(argv)
    return 0 if check_skill_registry(args.skill_json) else 1


if __name__ == "__main__":
    sys.exit(main())
