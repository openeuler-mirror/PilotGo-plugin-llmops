#!/usr/bin/env python3
"""
将 part1 的每个 Python 文件拆分为独立的可提交单元
目标：约 2000 个 PR

拆分策略：
1. 每个顶层函数 → 一个独立 .py 文件
2. 每个文件的完整内容 → 一个 PR（作为整合文件）
3. TOOL_CONFIG → 单独一个文件
4. __init__.py → 每个目录一个
5. cmd_safety_guard.py / assistant_identity.py → 按函数拆分

输出：
  - split/ 目录：拆分后的文件
  - pr_plan.json：每个文件的 PR 信息
"""

import os
import ast
import re
import json

PART1_DIR = "/home/syq/桌面/mcp_tools_part1"
SPLIT_DIR = "/home/syq/桌面/mcp_tools_part1/split"
# 目标仓库中 mcp_tools 的路径前缀
REPO_PREFIX = "mcps/mcp_tools"


def extract_imports_block(source):
    """提取所有 import 语句（含空行分隔）"""
    lines = source.split('\n')
    imports = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            imports.append(line)
        elif stripped.startswith('#') and not imports:
            continue  # 跳过文件头的注释
        elif stripped == '' and imports:
            imports.append('')
        elif imports:
            break
    while imports and imports[-1].strip() == '':
        imports.pop()
    return '\n'.join(imports)


def extract_logging_block(source):
    """提取 logging 配置块"""
    lines = source.split('\n')
    result = []
    in_basicConfig = False
    for line in lines:
        if 'logging.basicConfig' in line:
            in_basicConfig = True
        if in_basicConfig:
            result.append(line)
            if ')' in line and not line.strip().endswith(','):
                in_basicConfig = False
        if not in_basicConfig and re.match(r'\s*logger\s*=\s*logging\.getLogger', line):
            result.append(line)
    return '\n'.join(result)


def extract_tool_config_block(source):
    """提取 TOOL_CONFIG 块"""
    m = re.search(r'(TOOL_CONFIG\s*=\s*\{.+?\n\})', source, re.DOTALL)
    return m.group(1) if m else None


def get_func_source(lines, func_node):
    """从行号获取函数源码"""
    start = func_node.lineno - 1
    end = func_node.end_lineno if hasattr(func_node, 'end_lineno') else func_node.lineno
    return '\n'.join(lines[start:end])


def build_file_content(imports, logging_cfg, func_source, tool_config=None):
    """构建独立文件内容"""
    parts = ['#!/usr/bin/env python3']
    if imports:
        parts.append('')
        parts.append(imports)
    if logging_cfg:
        parts.append('')
        parts.append(logging_cfg)
    parts.append('')
    parts.append('')
    parts.append(func_source)
    if tool_config:
        parts.append('')
        parts.append('')
        parts.append(tool_config)
    return '\n'.join(parts) + '\n'


def split_file(filepath):
    """拆分一个文件为多个单元"""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.split('\n')
    imports = extract_imports_block(source)
    logging_cfg = extract_logging_block(source)
    tool_config = extract_tool_config_block(source)

    rel_path = os.path.relpath(filepath, PART1_DIR)
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    dir_part = os.path.dirname(rel_path)  # e.g. "ngx_mgmt"

    # 目标路径前缀
    repo_dir = f"{REPO_PREFIX}/{dir_part}" if dir_part else REPO_PREFIX

    results = []

    # 1. 每个顶层函数 → 一个独立文件
    functions = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.FunctionDef)]

    for func in functions:
        func_name = func.name
        func_source = get_func_source(lines, func)

        # 判断 TOOL_CONFIG 是否属于此函数
        func_tool_config = None
        if tool_config and (f"'{func_name}'" in tool_config or f'"{func_name}"' in tool_config):
            # 更精确检查：function 字段匹配
            if f"'function': '{func_name}'" in tool_config or f'"function": "{func_name}"' in tool_config:
                func_tool_config = tool_config

        content = build_file_content(imports, logging_cfg, func_source, func_tool_config)

        # 文件名: 原文件名__函数名.py
        out_name = f"{base_name}__{func_name}.py"
        out_rel = os.path.join(dir_part, out_name) if dir_part else out_name
        # 在仓库中的路径
        repo_path = f"{repo_dir}/{out_name}"

        results.append({
            'local_path': os.path.join(SPLIT_DIR, out_rel),
            'repo_path': repo_path,
            'content': content,
            'commit_msg': f"feat(mcp): add {dir_part} tool {func_name}" if dir_part else f"feat(mcp): add tool {func_name}",
            'type': 'function',
            'func_name': func_name,
            'original_file': rel_path,
        })

    # 2. 原始完整文件 → 一个 PR
    repo_full_path = f"{repo_dir}/{os.path.basename(filepath)}"
    results.append({
        'local_path': filepath,
        'repo_path': repo_full_path,
        'content': source,
        'commit_msg': f"feat(mcp): add {dir_part} module {base_name}" if dir_part else f"feat(mcp): add module {base_name}",
        'type': 'full_file',
        'original_file': rel_path,
    })

    # 3. TOOL_CONFIG → 单独文件（如果存在）
    if tool_config:
        tc_content = '#!/usr/bin/env python3\n' + ('\n' + imports if imports else '') + '\n\n' + tool_config + '\n'
        tc_name = f"{base_name}__TOOL_CONFIG.py"
        tc_rel = os.path.join(dir_part, tc_name) if dir_part else tc_name
        tc_repo_path = f"{repo_dir}/{tc_name}"
        results.append({
            'local_path': os.path.join(SPLIT_DIR, tc_rel),
            'repo_path': tc_repo_path,
            'content': tc_content,
            'commit_msg': f"feat(mcp): add {dir_part} config for {base_name}" if dir_part else f"feat(mcp): add config for {base_name}",
            'type': 'tool_config',
            'original_file': rel_path,
        })

    return results


def generate_init_files():
    """为每个目录生成 __init__.py"""
    results = []
    dirs = set()
    for root, ds, files in os.walk(PART1_DIR):
        ds[:] = [d for d in ds if d not in ('syq', 'yzy', 'split', '__pycache__', '.git')]
        for d in ds:
            rel = os.path.relpath(os.path.join(root, d), PART1_DIR)
            dirs.add(rel)

    for d in sorted(dirs):
        repo_path = f"{REPO_PREFIX}/{d}/__init__.py"
        content = '#!/usr/bin/env python3\n"""MCP tools package."""\n'
        results.append({
            'local_path': os.path.join(SPLIT_DIR, d, '__init__.py'),
            'repo_path': repo_path,
            'content': content,
            'commit_msg': f"feat(mcp): add {d} package init",
            'type': 'init',
        })

    # 顶层 __init__.py
    results.append({
        'local_path': os.path.join(SPLIT_DIR, '__init__.py'),
        'repo_path': f"{REPO_PREFIX}/__init__.py",
        'content': '#!/usr/bin/env python3\n"""MCP tools package."""\n',
        'commit_msg': 'feat(mcp): add mcp_tools package init',
        'type': 'init',
    })

    return results


def main():
    os.makedirs(SPLIT_DIR, exist_ok=True)

    all_entries = []

    # 拆分所有 py 文件
    for root, dirs, files in os.walk(PART1_DIR):
        dirs[:] = [d for d in dirs if d not in ('syq', 'yzy', 'split', '__pycache__', '.git')]
        for f in files:
            if not f.endswith('.py'):
                continue
            filepath = os.path.join(root, f)
            entries = split_file(filepath)
            all_entries.extend(entries)

    # 添加 __init__.py
    all_entries.extend(generate_init_files())

    # 写入拆分文件
    for entry in all_entries:
        if entry['type'] == 'full_file':
            continue  # 原始文件已存在
        out_dir = os.path.dirname(entry['local_path'])
        os.makedirs(out_dir, exist_ok=True)
        with open(entry['local_path'], 'w', encoding='utf-8') as f:
            f.write(entry['content'])

    # 统计
    func_count = sum(1 for e in all_entries if e['type'] == 'function')
    full_count = sum(1 for e in all_entries if e['type'] == 'full_file')
    tc_count = sum(1 for e in all_entries if e['type'] == 'tool_config')
    init_count = sum(1 for e in all_entries if e['type'] == 'init')

    print(f"拆分完成!")
    print(f"  函数文件: {func_count}")
    print(f"  完整文件: {full_count}")
    print(f"  TOOL_CONFIG: {tc_count}")
    print(f"  __init__.py: {init_count}")
    print(f"  总PR数: {len(all_entries)}")

    # 保存 PR 计划
    plan_path = os.path.join(PART1_DIR, 'pr_plan.json')
    # 分配到两个账号
    # 策略：函数文件交替分配，完整文件和 TOOL_CONFIG 给账号1，init 给账号2
    acc1_entries = []
    acc2_entries = []

    for i, entry in enumerate(all_entries):
        if entry['type'] == 'function':
            if i % 2 == 0:
                acc1_entries.append(entry)
            else:
                acc2_entries.append(entry)
        elif entry['type'] == 'full_file':
            acc1_entries.append(entry)
        elif entry['type'] == 'tool_config':
            acc2_entries.append(entry)
        elif entry['type'] == 'init':
            acc1_entries.append(entry)

    plan = {
        'account1': {
            'owner': 'songyuqin0686',
            'count': len(acc1_entries),
            'entries': acc1_entries,
        },
        'account2': {
            'owner': 'yzydev',
            'count': len(acc2_entries),
            'entries': acc2_entries,
        },
        'total': len(all_entries),
    }

    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"\nPR计划已保存到: {plan_path}")
    print(f"  账号1 (songyuqin0686): {len(acc1_entries)} 个PR")
    print(f"  账号2 (yzydev): {len(acc2_entries)} 个PR")


if __name__ == '__main__':
    main()
