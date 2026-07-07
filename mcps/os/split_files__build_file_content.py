#!/usr/bin/env python3

import os
import ast
import re
import json

        if 'logging.basicConfig' in line:
            in_basicConfig = True
        if in_basicConfig:
            result.append(line)


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
