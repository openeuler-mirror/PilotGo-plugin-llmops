#!/usr/bin/env python3

import os
import ast
import re
import json


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
