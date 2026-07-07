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


def save_config_file(cfg_filepath: str) -> Optional[str]:
    """备份配置文件"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"save_config_file: cfg_filepath 路径验证失败：{error_msg}")
            return None

        timestamp = subprocess.getoutput('date +%Y%m%d_%H%M%S')
        backup_dir = '/tmp/nginx_config_backups'  # NOSONAR
        Path(backup_dir).mkdir(exist_ok=True)

        backup_filename = f"{os.path.basename(cfg_filepath)}.backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(cfg_filepath, backup_path)
        return backup_path

    except Exception as e:
        logger.error(f'备份配置文件失败: {e}')
        return None
