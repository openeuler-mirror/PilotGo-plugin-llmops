#!/usr/bin/env python3

import json
import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_weight')


def store_nginx_config(cfg_filepath: str, body: str) -> bool:
    """
    写入 Nginx 配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        body: 配置文件内容
        
    返回:
        bool: 是否写入成功
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"store_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return False
        
        # 创建备份
        backup_path = f"{cfg_filepath}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 安全验证：验证 backup_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(backup_path, allow_absolute=True)
        if not valid:
            logger.error(f"store_nginx_config: backup_path 路径验证失败：{error_msg}")
            return False
        
        subprocess.run(['cp', cfg_filepath, backup_path], check=True)
        
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(body)
        
        logger.info(f"配置文件已更新，备份保存在: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"写入Nginx配置文件失败 {cfg_filepath}: {e}")
        return False
