#!/usr/bin/env python3

import subprocess
import psutil
import os
import time
import logging
from datetime import datetime
import signal

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')


def fetch_nginx_master_pids():
    """
    获取Nginx主进程PID列表

    Returns:
        list: 主进程PID列表
    """
    try:
        pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['name'] and 'nginx' in proc.info['name'].lower() and
                    proc.info['cmdline'] and 'master' in ' '.join(proc.info['cmdline']).lower()):
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids
    except Exception as e:
        logger.error(f"获取Nginx主进程PID失败: {e}")
        return []
