#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
import subprocess
import sys

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_config_line(line: str) -> Dict[str, Any]:
    """
    解析配置文件行

    参数:
        line: 配置文件行

    返回:
        解析后的配置行信息字典
    """
    output = {
        'raw_line': line,
        'is_comment': False,
        'is_empty': False,
        'is_directive': False,
        'directive': '',
        'val': '',
        'comment': ''
    }

    stripped_line = line.strip()

    if not stripped_line:
        output['is_empty'] = True
        return output

    if stripped_line.startswith('#'):
        output['is_comment'] = True
        output['comment'] = stripped_line[1:].strip()
        return output

    if stripped_line.startswith('include ') or stripped_line.startswith('include\t'):
        output['is_directive'] = True
        parts = stripped_line.split(None, 1)
        output['directive'] = parts[0]
        output['val'] = parts[1].strip() if len(parts) > 1 else ''
        return output

    if ' ' in stripped_line or '\t' in stripped_line:
        parts = stripped_line.split(None, 1)
        if parts:
            output['directive'] = parts[0]
            if len(parts) > 1:
                output['val'] = parts[1]

                if '#' in output['val']:
                    value_parts = output['val'].split('#', 1)
                    output['val'] = value_parts[0].strip()
                    output['comment'] = value_parts[1].strip()

    return output
