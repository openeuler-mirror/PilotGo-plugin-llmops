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


def analyze_retry_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析重试配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 重试配置信息
    """
    retry_config = {
        'max_fails': 1,
        'fail_timeout': '10s',
        'proxy_next_upstream': 'error timeout',
        'proxy_next_upstream_tries': 0,
        'proxy_next_upstream_timeout': 0
    }
    
    try:
        # 解析max_fails和fail_timeout（在server级别）
        max_fails_match = re.search(r'max_fails=(\d+)', upstream_content)  # NOSONAR
        if max_fails_match:
            retry_config['max_fails'] = int(max_fails_match.group(1))
        
        fail_timeout_match = re.search(r'fail_timeout=([\d]+[smh]?)', upstream_content)  # NOSONAR
        if fail_timeout_match:
            retry_config['fail_timeout'] = fail_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析重试配置失败: {e}")
    
    return retry_config
