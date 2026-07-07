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


def replace_log_paths(body: str, pattern: str, new_path: str, log_type: str) -> Tuple[str, List[Dict]]:
    """替换日志路径"""
    changes = []

    try:
        # 安全验证：验证 new_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(new_path, allow_absolute=True)
        if not valid:
            logger.error(f"replace_log_paths: new_path 路径验证失败：{error_msg}")
            return body, changes

        def replacement(match):
            old_path = match.group(2).strip()
            change_info = {
                'type': log_type,
                'old_path': old_path,
                'new_path': new_path,
                'line_content': match.group(0)
            }
            changes.append(change_info)

            return match.group(1) + new_path + match.group(3)

        modified_content = re.sub(pattern, replacement, body)  # NOSONAR
        return modified_content, changes

    except Exception as e:
        logger.error(f'替换日志路径失败: {e}')
        return body, []
