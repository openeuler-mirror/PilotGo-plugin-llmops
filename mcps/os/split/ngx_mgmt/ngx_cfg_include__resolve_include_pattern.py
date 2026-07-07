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


def resolve_include_pattern(pattern: str) -> List[Dict[str, Union[str, bool, int]]]:
    """
    解析include模式，返回匹配的文件列表

    参数:
        pattern: include模式（可能包含通配符）

    返回:
        list: 包含匹配文件信息的字典列表
    """
    resolved_files = []

    try:
        # 如果没有通配符，直接检查文件是否存在
        if '*' not in pattern and '?' not in pattern:
            if os.path.isfile(pattern):
                file_stat = os.stat(pattern)
                resolved_files.append({
                    'path': pattern,
                    'exists': True,
                    'is_readable': os.access(pattern, os.R_OK),
                    'size': file_stat.st_size,
                    'modified_time': file_stat.st_mtime
                })
            else:
                resolved_files.append({
                    'path': pattern,
                    'exists': False,
                    'is_readable': False,
                    'error': '文件不存在'
                })
            return resolved_files

        # 处理通配符
        dir_path = os.path.dirname(pattern)
        file_pattern = os.path.basename(pattern)

        # 转换通配符为正则表达式
        regex_pattern = file_pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')  # NOSONAR
        regex_pattern = f'^{regex_pattern}$'

        # 检查目录是否存在
        if not os.path.exists(dir_path):
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'目录不存在: {dir_path}'
            })
            return resolved_files

        # 查找匹配的文件
        try:
            for file_name in os.listdir(dir_path):
                if re.match(regex_pattern, file_name):  # NOSONAR
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        resolved_files.append({
                            'path': file_path,
                            'exists': True,
                            'is_readable': os.access(file_path, os.R_OK),
                            'size': file_stat.st_size,
                            'modified_time': file_stat.st_mtime
                        })
        except PermissionError:
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'没有权限读取目录: {dir_path}'
            })

        # 如果没有找到匹配的文件
        if not resolved_files:
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'没有找到匹配的文件: {pattern}'
            })

        # 按修改时间排序（加载顺序）
        resolved_files.sort(key=lambda x: x.get('modified_time', 0))

        return resolved_files

    except Exception as e:
        logger.error(f'解析include模式失败: {e}')
        return [{
            'path': pattern,
            'exists': False,
            'is_readable': False,
            'error': f'解析失败: {e}'
        }]
