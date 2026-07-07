#!/usr/bin/env python3

import os
import ast
import re
import json


def extract_tool_config_block(source):
    """提取 TOOL_CONFIG 块"""
    m = re.search(r'(TOOL_CONFIG\s*=\s*\{.+?\n\})', source, re.DOTALL)
    return m.group(1) if m else None
