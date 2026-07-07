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


def fetch_nested_includes(file_path: str, max_depth: int = 5, current_depth: int = 0, visited_files: set = None) -> Dict:
    """
    递归获取嵌套的include指令

    参数:
        file_path: 配置文件路径
        max_depth: 最大递归深度
        current_depth: 当前递归深度
        visited_files: 已访问的文件集合（防止循环引用）

    返回:
        dict: 包含嵌套include信息的字典
    """
    visited_files = set() if visited_files is None else visited_files
    # 防止循环引用
    if file_path in visited_files or current_depth >= max_depth:
        return {
            'file_path': file_path,
            'includes': [],
            'error': '已达到最大递归深度或检测到循环引用'
        }

    visited_files.add(file_path)

    try:
        # 读取文件内容
        body = Path(file_path).read_text()

        # 解析include指令
        base_dir = os.path.dirname(file_path)
        includes = analyze_include_directives(body, base_dir)

        # 递归处理每个include
        for include in includes:
            pattern = include['full_pattern']
            resolved_files = resolve_include_pattern(pattern)
            include['resolved_files'] = resolved_files

            # 递归处理每个解析出的文件
            for file_info in resolved_files:
                if file_info.get('exists', False) and file_info.get('is_readable', False):
                    nested_path = file_info['path']
                    nested_result = fetch_nested_includes(
                        nested_path,
                        max_depth,
                        current_depth + 1,
                        visited_files.copy()
                    )
                    file_info['nested_includes'] = nested_result

        return {
            'file_path': file_path,
            'includes': includes,
            'depth': current_depth
        }

    except Exception as e:
        logger.error(f'获取嵌套include失败: {e}')
        return {
            'file_path': file_path,
            'includes': [],
            'error': f'处理文件失败: {e}'
        }
