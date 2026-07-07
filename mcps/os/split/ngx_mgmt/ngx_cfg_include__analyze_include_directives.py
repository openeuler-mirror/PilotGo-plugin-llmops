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


def analyze_include_directives(body: str, base_dir: str = '') -> List[Dict[str, Union[str, int, bool]]]:
    """
    解析配置文件中的include指令

    参数:
        body: 配置文件内容
        base_dir: 配置文件所在目录，用于解析相对路径

    返回:
        list: 包含include指令信息的字典列表
    """
    includes = []

    try:
        # 查找所有include指令
        include_patterns = re.findall(r'include\s+([^\s;]+)', body)  # NOSONAR

        for i, pattern in enumerate(include_patterns):
            # 获取include指令在文件中的行号
            line_number = fetch_include_line_number(body, pattern, i)

            # 解析路径
            is_absolute = os.path.isabs(pattern)
            has_wildcard = '*' in pattern or '?' in pattern

            # 处理路径
            full_pattern = os.path.join(base_dir, pattern) if not is_absolute and base_dir else pattern
            includes.append({
                'index': i + 1,
                'pattern': pattern,
                'full_pattern': full_pattern,
                'is_absolute': is_absolute,
                'has_wildcard': has_wildcard,
                'line_number': line_number,
                'resolved_files': []
            })

        return includes

    except Exception as e:
        logger.error(f'解析include指令失败: {e}')
        return []
