#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.cmd_safety_guard import validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(msg)s',
)
logger = logging.getLogger('nginx_set_config_check')


def analyze_error_line(error_line: str, config_path: str, config_content: Optional[str] = None) -> Optional[Dict]:
    """解析单行错误信息"""
    try:
        # 常见的Nginx错误模式
        patterns = [
            # 模式1: nginx: [emerg] invalid parameter "xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*(.+?)\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式2: nginx: [emerg] unknown directive "xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*unknown directive\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式3: nginx: [emerg] directive "xxx" is not terminated by ";" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*directive\s+"([^"]+)"\s+is not terminated by\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式4: nginx: [emerg] invalid number of arguments in "xxx" directive in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*invalid number of arguments in\s+"([^"]+)"\s+directive\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式5: nginx: [emerg] host not found in "xxx" of the "listen" directive in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*host not found in\s+"([^"]+)"\s+of the\s+"([^"]+)"\s+directive\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式6: nginx: [emerg] duplicate location "/xxx" in /path/to/file:line
            r'nginx:\s*\[emerg\]\s*duplicate\s+([^"]+)\s+"([^"]+)"\s+in\s+(.+?):(\d+)',  # NOSONAR

            # 模式7: nginx: [warn] ...
            r'nginx:\s*\[warn\]\s*(.+)',

            # 模式8: 通用错误模式
            r'nginx:\s*\[emerg\]\s*(.+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, error_line, re.IGNORECASE)  # NOSONAR
            if match:
                groups = match.groups()

                # 根据模式类型处理
                if pattern == patterns[0]:  # 模式1
                    return {
                        'line_number': int(groups[2]),
                        'msg': groups[0],
                        'error_type': 'invalid_parameter',
                        'directive': derive_directive_from_context(groups[0]),
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[1]:  # 模式2
                    return {
                        'line_number': int(groups[2]),
                        'msg': f'未知指令: {groups[0]}',
                        'error_type': 'unknown_directive',
                        'directive': groups[0],
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[2]:  # 模式3
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'指令 "{groups[0]}" 未以 "{groups[1]}" 结尾',
                        'error_type': 'unterminated_directive',
                        'directive': groups[0],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[3]:  # 模式4
                    return {
                        'line_number': int(groups[2]),
                        'msg': f'指令 "{groups[0]}" 参数数量无效',
                        'error_type': 'invalid_arguments',
                        'directive': groups[0],
                        'file_path': groups[1],
                        'severity': 'error'
                    }

                elif pattern == patterns[4]:  # 模式5
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'在 "{groups[1]}" 指令中找不到主机 "{groups[0]}"',
                        'error_type': 'host_not_found',
                        'directive': groups[1],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[5]:  # 模式6
                    return {
                        'line_number': int(groups[3]),
                        'msg': f'重复的 {groups[0]}: {groups[1]}',
                        'error_type': 'duplicate_config',
                        'config_type': groups[0],
                        'file_path': groups[2],
                        'severity': 'error'
                    }

                elif pattern == patterns[6]:  # 模式7
                    return {
                        'line_number': 0,
                        'msg': groups[0],
                        'error_type': 'warning',
                        'severity': 'warning'
                    }

                elif pattern == patterns[7]:  # 模式8
                    return {
                        'line_number': 0,
                        'msg': groups[0],
                        'error_type': 'general_error',
                        'severity': 'error'
                    }

        # 如果未匹配任何模式，返回通用错误
        return {
            'line_number': 0,
            'msg': error_line.strip(),
            'error_type': 'unknown_error',
            'severity': 'error'
        }

    except Exception as e:
        logger.error(f'解析错误行失败: {e}')
        return None
