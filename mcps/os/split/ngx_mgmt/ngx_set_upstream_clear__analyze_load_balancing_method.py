#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_clear')


def analyze_load_balancing_method(upstream_content: str) -> str:
    """
    解析负载均衡策略
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        str: 负载均衡策略
    """
    lb_method = 'round-robin'  # 默认轮询
    
    try:
        if re.search(r'ip_hash', upstream_content):  # NOSONAR
            lb_method = 'ip_hash'
        elif re.search(r'least_conn', upstream_content):  # NOSONAR
            lb_method = 'least_conn'
        elif re.search(r'hash', upstream_content):  # NOSONAR
            hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
            if hash_match:
                lb_method = f'hash {hash_match.group(1)}'
        elif re.search(r'fair', upstream_content):  # NOSONAR
            lb_method = 'fair'
        elif re.search(r'url_hash', upstream_content):  # NOSONAR
            lb_method = 'url_hash'
        
    except Exception as e:
        logger.error(f"解析负载均衡策略失败: {e}")
    
    return lb_method
