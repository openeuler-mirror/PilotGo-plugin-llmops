#!/usr/bin/env python3

import subprocess
import platform
import os
import re
import logging
import time
import threading
import select
from datetime import datetime
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from .utils import (

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_real_time')


def fetch_nginx_config_info():
    """
    获取Nginx配置信息（从utils.py复制）
    """
    try:
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        
        cfg_state = {
            'config_file': 'Unknown'
        }
        
        if output.returncode == 0:
            config_match = re.search(r'file ([^\s]+) test is successful', output.stdout)  # NOSONAR
            if config_match:
                cfg_state['config_file'] = config_match.group(1)
        else:
            config_match = re.search(r'file ([^\s]+)', output.stdout)  # NOSONAR
            if config_match:
                cfg_state['config_file'] = config_match.group(1)
        
        if cfg_state['config_file'] == 'Unknown':
            common_paths = ['/etc/nginx/nginx.conf', '/usr/local/nginx/conf/nginx.conf']
            for path in common_paths:
                if os.path.exists(path):
                    cfg_state['config_file'] = path
                    break
        
        return cfg_state
        
    except Exception as e:
        logger.error(f'获取Nginx配置信息失败: {e}')
        return {
            'config_file': '获取失败'
        }
