#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import glob
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_path_modify')


def verify_nginx_syntax(cfg_filepath: str) -> Dict:
    """检查 Nginx 配置语法"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"verify_nginx_syntax: cfg_filepath 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'errors': [f'配置文件路径不安全：{error_msg}']
            }

        output = subprocess.run(['nginx', '-t', '-c', cfg_filepath], capture_output=True, text=True, timeout=30)

        errors = []
        if output.returncode != 0:
            error_output = output.stderr or output.stdout
            error_lines = error_output.split('\n')
            for line in error_lines:
                if 'emerg' in line.lower() or 'error' in line.lower():
                    errors.append(line.strip())

        return {
            'valid': output.returncode == 0,
            'errors': errors,
            'output': error_output if output.returncode != 0 else 'Syntax OK'
        }

    except subprocess.TimeoutExpired:
        return {
            'valid': False,
            'errors': ['语法检查超时'],
            'output': 'Timeout'
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f'语法检查失败: {e}'],
            'output': str(e)
        }
