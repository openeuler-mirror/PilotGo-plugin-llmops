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


def modify_log_paths_in_content(body: str,
                               access_log_path: Optional[str],
                               error_log_path: Optional[str],
                               current_logs: Dict) -> Tuple[str, List[Dict]]:
    """在配置内容中修改日志路径"""
    changes = []
    modified_content = body

    try:
        # 安全验证：验证 access_log_path 路径参数（如果提供，允许绝对路径）
        if access_log_path is not None:
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_log_paths_in_content: access_log_path 路径验证失败：{error_msg}")
                return body, changes

        # 安全验证：验证 error_log_path 路径参数（如果提供，允许绝对路径）
        if error_log_path is not None:
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_log_paths_in_content: error_log_path 路径验证失败：{error_msg}")
                return body, changes

        # 修改访问日志路径
        if access_log_path:
            # 处理主配置文件中的访问日志
            access_log_pattern = r'(access_log\s+)([^;]+)(;)'  # NOSONAR
            modified_content, access_changes = replace_log_paths(
                modified_content, access_log_pattern, access_log_path, 'access_log'
            )
            changes.extend(access_changes)

        # 修改错误日志路径
        if error_log_path:
            # 处理主配置文件中的错误日志
            error_log_pattern = r'(error_log\s+)([^;]+)(;)'  # NOSONAR
            modified_content, error_changes = replace_log_paths(
                modified_content, error_log_pattern, error_log_path, 'error_log'
            )
            changes.extend(error_changes)

        return modified_content, changes

    except Exception as e:
        logger.error(f'修改日志路径失败: {e}')
        return body, changes
