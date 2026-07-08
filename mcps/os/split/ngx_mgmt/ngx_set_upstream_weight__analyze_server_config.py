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


def analyze_server_config(server_line: str) -> Dict[str, Any]:
    """
    解析服务器配置参数
    
    参数:
        server_line: 服务器配置行
        
    返回:
        dict: 服务器配置信息
    """
    server_info = {
        'address': '',
        'port': 80,
        'weight': 1,
        'max_fails': 1,
        'fail_timeout': '10s',
        'max_conns': 0,
        'backup': False,
        'down': False
    }
    
    try:
        # 提取服务器地址
        parts = server_line.split()
        if len(parts) > 1:
            address_part = parts[1]
            if ':' in address_part:
                addr_parts = address_part.split(':')
                server_info['address'] = addr_parts[0]
                server_info['port'] = int(addr_parts[1]) if addr_parts[1].isdigit() else 80
            else:
                server_info['address'] = address_part
        
        # 解析参数
        for part in parts[2:]:
            part = part.rstrip(';')
            if part == 'backup':
                server_info['backup'] = True
            elif part == 'down':
                server_info['down'] = True
            elif part.startswith('weight='):
                server_info['weight'] = int(part.split('=')[1])
            elif part.startswith('max_fails='):
                server_info['max_fails'] = int(part.split('=')[1])
            elif part.startswith('fail_timeout='):
                server_info['fail_timeout'] = part.split('=')[1]
            elif part.startswith('max_conns='):
                server_info['max_conns'] = int(part.split('=')[1])
        
    except Exception as e:
        logger.error(f"解析服务器配置失败 {server_line}: {e}")
    
    return server_info
