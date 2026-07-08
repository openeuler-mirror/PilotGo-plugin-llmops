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


def invoke_syntax_check(config_path: str) -> Dict:
    """执行 Nginx 语法检查"""
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_path, allow_absolute=True)
        if not valid:
            logger.error(f"invoke_syntax_check: config_path 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'returncode': -1,
                'stdout': '',
                'stderr': f'配置文件路径不安全：{error_msg}',
                'check_time': 0.0,
                'nginx_version': 'Unknown'
            }

        start_time = subprocess.getoutput('date +%s.%N')

        # 执行nginx -t命令
        output = subprocess.run(
            ['nginx', '-t', '-c', config_path],
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时
        )

        end_time = subprocess.getoutput('date +%s.%N')
        check_time = float(end_time) - float(start_time)

        # 获取Nginx版本
        version_result = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        nginx_version = 'Unknown'
        if version_result.returncode == 0:
            ver_match = re.search(r'nginx/([\d\.]+)', version_result.stderr or version_result.stdout)  # NOSONAR
            if ver_match:
                nginx_version = ver_match.group(1)

        return {
            'valid': output.returncode == 0,
            'returncode': output.returncode,
            'stdout': output.stdout,
            'stderr': output.stderr,
            'check_time': check_time,
            'nginx_version': nginx_version
        }

    except subprocess.TimeoutExpired:
        logger.error('语法检查超时')
        return {
            'valid': False,
            'returncode': -1,
            'stdout': '',
            'stderr': '语法检查超时（超过30秒）',
            'check_time': 30.0,
            'nginx_version': 'Unknown'
        }
    except Exception as e:
        logger.error(f'执行语法检查失败: {e}')
        return {
            'valid': False,
            'returncode': -1,
            'stdout': '',
            'stderr': f'执行语法检查失败: {e}',
            'check_time': 0.0,
            'nginx_version': 'Unknown'
        }
