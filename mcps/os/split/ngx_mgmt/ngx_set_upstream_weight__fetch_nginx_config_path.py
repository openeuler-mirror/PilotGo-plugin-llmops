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


def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: Nginx配置文件路径，如果找不到返回None
    """
    try:
        # 检查Nginx进程获取配置文件路径
        for proc in psutil.process_iter(['name', 'cmdline']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                cmdline = proc.info['cmdline'] or []
                for i, arg in enumerate(cmdline):
                    if arg == '-c' and i + 1 < len(cmdline):
                        return cmdline[i + 1]
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf',
            '/etc/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 尝试通过nginx -t命令获取配置路径
        try:
            output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, timeout=10)
            if output.returncode == 0:
                for line in output.stderr.split('\n'):
                    if 'nginx.conf' in line:
                        match = re.search(r'file\s+([^\s]+)', line)  # NOSONAR
                        if match:
                            return match.group(1)
        except Exception:
            pass
        
        logger.warning("无法找到Nginx配置文件")
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None
