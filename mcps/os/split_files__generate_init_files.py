#!/usr/bin/env python3

import os
import ast
import re
import json


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
