#!/usr/bin/env python3

import os
import ast
import re
import json


def extract_logging_block(source):
    """提取 logging 配置块"""
    lines = source.split('\n')
    result = []
    in_basicConfig = False
    for line in lines:
        stripped = line.strip()
        # 只匹配实际的 logging.basicConfig 调用，而不是包含这个字符串的代码
        if stripped.startswith('logging.basicConfig') or stripped.startswith('logging.basicConfig('):
            in_basicConfig = True
        if in_basicConfig:
            result.append(line)
            if ')' in line and not line.strip().endswith(','):
                in_basicConfig = False
        if not in_basicConfig and re.match(r'\s*logger\s*=\s*logging\.getLogger', line):
            result.append(line)
    return '\n'.join(result)
