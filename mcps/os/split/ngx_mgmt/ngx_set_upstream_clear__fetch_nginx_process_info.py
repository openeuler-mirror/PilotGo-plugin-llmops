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


def fetch_nginx_process_info() -> Optional[Dict[str, Any]]:
    """
    获取Nginx进程信息
    
    返回:
        dict: Nginx进程信息
    """
    try:
        nginx_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    nginx_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                        'status': proc.status()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'process_count': len(nginx_processes),
            'processes': nginx_processes,
            'master_pid': nginx_processes[0]['pid'] if nginx_processes else None
        }
        
    except Exception as e:
        logger.error(f"获取Nginx进程信息失败: {e}")
        return None
