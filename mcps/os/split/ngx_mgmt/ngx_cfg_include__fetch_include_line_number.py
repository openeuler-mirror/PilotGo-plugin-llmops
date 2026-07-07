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


def fetch_include_line_number(body: str, pattern: str, occurrence: int) -> int:
    """
    获取include指令在文件中的行号

    参数:
        body: 文件内容
        pattern: include模式
        occurrence: 出现次数索引

    返回:
        int: 行号
    """
    try:
        lines = body.split('\n')
        count = 0

        for i, line in enumerate(lines):
            if re.search(rf'include\s+{re.escape(pattern)}', line):  # NOSONAR
                if count == occurrence:
                    return i + 1
                count += 1

        return -1

    except Exception as e:
        logger.error(f'获取include指令行号失败: {e}')
        return -1
