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


def locate_server_in_upstream(upstream_content: str, server_address: str) -> Tuple[Optional[str], int, int]:
    """
    在upstream块中查找指定服务器配置
    
    参数:
        upstream_content: upstream块内容
        server_address: 服务器地址
        
    返回:
        tuple: (服务器配置行, 起始位置, 结束位置)
    """
    try:
        # 构建服务器地址匹配模式
        server_pattern = rf'server\s+{re.escape(server_address)}(?:\s+[^;]+)*;'  # NOSONAR
        match = re.search(server_pattern, upstream_content)  # NOSONAR
        
        if not match:
            # 尝试不带端口号的匹配
            address_only = server_address.split(':')[0]
            server_pattern = rf'server\s+{re.escape(address_only)}(?:\s+[^;]+)*;'  # NOSONAR
            match = re.search(server_pattern, upstream_content)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        server_line = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        return server_line, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找服务器配置失败 {server_address}: {e}")
        return None, -1, -1
