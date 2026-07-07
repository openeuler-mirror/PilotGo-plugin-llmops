#!/usr/bin/env python3

import os
import ast
import re
import json

        if 'logging.basicConfig' in line:
            in_basicConfig = True
        if in_basicConfig:
            result.append(line)


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
