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


def verify_nginx_config(cfg_filepath: str) -> bool:
    """
    检查 Nginx 配置语法
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        bool: 配置语法是否正确
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"verify_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return False
        
        output = subprocess.run(['nginx', '-t', '-c', cfg_filepath], 
                              capture_output=True, text=True, timeout=30)
        
        if output.returncode == 0:
            logger.info("Nginx配置语法检查通过")
            return True
        else:
            logger.error(f"Nginx配置语法检查失败: {output.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"检查Nginx配置语法失败: {e}")
        return False
