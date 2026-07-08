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


def build_server_config(server_info: Dict[str, Any], new_weight: int) -> str:
    """
    构建新的服务器配置行
    
    参数:
        server_info: 服务器配置信息
        new_weight: 新的权重值
        
    返回:
        str: 新的服务器配置行
    """
    try:
        # 构建基础配置
        address = server_info['address']
        if server_info['port'] != 80:
            address = f"{address}:{server_info['port']}"
        
        config_parts = ['server', address]
        
        # 添加权重参数
        config_parts.append(f"weight={new_weight}")
        
        # 添加其他参数
        if server_info['max_fails'] != 1:
            config_parts.append(f"max_fails={server_info['max_fails']}")
        
        if server_info['fail_timeout'] != '10s':
            config_parts.append(f"fail_timeout={server_info['fail_timeout']}")
        
        if server_info['max_conns'] > 0:
            config_parts.append(f"max_conns={server_info['max_conns']}")
        
        if server_info['backup']:
            config_parts.append('backup')
        
        if server_info['down']:
            config_parts.append('down')
        
        return ' '.join(config_parts) + ';'
        
    except Exception as e:
        logger.error(f"构建服务器配置失败: {e}")
        return ""
