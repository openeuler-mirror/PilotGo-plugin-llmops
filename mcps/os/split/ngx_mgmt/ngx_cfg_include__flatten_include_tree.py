#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_include')


def flatten_include_tree(include_tree: Dict, flat_list: List = None, level: int = 0) -> List[Dict]:
    """
    将嵌套的include树展平为列表

    参数:
        include_tree: include树
        flat_list: 展平后的列表
        level: 当前层级

    返回:
        list: 展平后的include列表
    """
    flat_list = [] if flat_list is None else flat_list
    if 'includes' in include_tree:
        for include in include_tree['includes']:
            include_info = {
                'level': level,
                'pattern': include['pattern'],
                'line_number': include['line_number'],
                'is_absolute': include['is_absolute'],
                'has_wildcard': include['has_wildcard']
            }

            for file_info in include.get('resolved_files', []):
                file_entry = include_info.copy()
                file_entry.update({
                    'file_path': file_info['path'],
                    'exists': file_info.get('exists', False),
                    'is_readable': file_info.get('is_readable', False),
                    'size': file_info.get('size', 0),
                    'modified_time': file_info.get('modified_time', 0)
                })

                if 'error' in file_info:
                    file_entry['error'] = file_info['error']

                flat_list.append(file_entry)

                # 递归处理嵌套include
                if file_info.get('exists', False) and 'nested_includes' in file_info:
                    flatten_include_tree(file_info['nested_includes'], flat_list, level + 1)

    return flat_list
