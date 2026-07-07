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


def build_log_directories(access_log_path: Optional[str], error_log_path: Optional[str]):
    """创建日志目录"""
    try:
        paths_to_create = set()

        if access_log_path:
            # 安全验证：验证 access_log_path 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"build_log_directories: access_log_path 路径验证失败：{error_msg}")
                return

            access_dir = os.path.dirname(access_log_path)
            if access_dir:
                paths_to_create.add(access_dir)

        if error_log_path:
            # 安全验证：验证 error_log_path 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"build_log_directories: error_log_path 路径验证失败：{error_msg}")
                return

            error_dir = os.path.dirname(error_log_path)
            if error_dir:
                paths_to_create.add(error_dir)

        for directory in paths_to_create:
            if directory and not os.path.exists(directory):
                Path(directory).mkdir(parents=True, exist_ok=True)
                # 设置适当的权限
                os.chmod(directory, 0o755)  # NOSONAR
                logger.info(f'创建日志目录：{directory}')

    except Exception as e:
        logger.error(f'创建日志目录失败: {e}')
