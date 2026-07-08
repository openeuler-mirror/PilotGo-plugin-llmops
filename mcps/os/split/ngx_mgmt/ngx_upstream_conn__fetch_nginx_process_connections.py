#!/usr/bin/env python3

import os
import re
import json
import logging
import subprocess
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_connection')


def fetch_nginx_process_connections() -> Dict[str, Any]:
    """
    获取Nginx进程连接数信息
    
    返回:
        dict: 进程连接数信息
    """
    connection_info = {
        'total_connections': 0,
        'active_connections': 0,
        'idle_connections': 0,
        'process_count': 0,
        'worker_processes': []
    }
    
    try:
        # 查找Nginx进程
        nginx_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    nginx_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        connection_info['process_count'] = len(nginx_processes)
        
        # 分析每个进程的连接数
        for proc in nginx_processes:
            try:
                connections = proc.connections()
                worker_info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'total_connections': len(connections),
                    'active_connections': len([c for c in connections if c.status == 'ESTABLISHED']),
                    'idle_connections': len([c for c in connections if c.status == 'LISTEN'])
                }
                
                connection_info['total_connections'] += worker_info['total_connections']
                connection_info['active_connections'] += worker_info['active_connections']
                connection_info['idle_connections'] += worker_info['idle_connections']
                connection_info['worker_processes'].append(worker_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
    except Exception as e:
        logger.error(f"获取Nginx进程连接数失败: {e}")
    
    return connection_info
