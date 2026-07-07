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


def fetch_current_log_paths(cfg_filepath: Optional[str] = None) -> Dict:
    """
    获取当前 Nginx 日志路径信息

    参数:
        cfg_filepath: 配置文件路径，如果为 None 则自动检测

    返回:
        Dict: 当前日志路径信息
    """
    try:
        if not cfg_filepath:
            cfg_filepath = fetch_nginx_config_path()
            if not cfg_filepath:
                return {
                    'success': False,
                    'message': '无法检测 Nginx 配置文件路径'
                }

        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_current_log_paths: cfg_filepath 路径验证失败：{error_msg}")
            return {
                'success': False,
                'message': f'配置文件路径不安全：{error_msg}'
            }

        body = Path(cfg_filepath).read_text(encoding='utf-8')

        current_logs = analyze_current_log_configs(body, cfg_filepath)

        return {
            'success': True,
            'message': '获取日志路径成功',
            'cfg_filepath': cfg_filepath,
            'access_logs': current_logs['access_logs'],
            'error_logs': current_logs['error_logs'],
            'include_files': current_logs['include_files']
        }

    except Exception as e:
        logger.error(f'获取当前日志路径失败: {e}')
        return {
            'success': False,
            'message': f'获取失败: {e}'
        }
