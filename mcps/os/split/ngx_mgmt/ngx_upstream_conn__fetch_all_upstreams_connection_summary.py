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


def fetch_all_upstreams_connection_summary() -> Dict[str, Any]:
    """
    获取所有upstream的连接数汇总
    
    返回:
        dict: 所有upstream连接数汇总信息
    """
    summary = {
        'total_upstreams': 0,
        'total_connections': 0,
        'total_active_connections': 0,
        'total_max_connections': 0,
        'upstreams_details': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取所有upstream配置
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            summary['error'] = '无法找到Nginx配置文件'
            return summary
        
        body = load_nginx_config(cfg_filepath)
        upstream_pattern = r'upstream\s+(\w+)\s*\{[^}]+\}'  # NOSONAR
        upstream_matches = re.findall(upstream_pattern, body)  # NOSONAR
        
        if not upstream_matches:
            summary['message'] = '未找到任何upstream配置'
            return summary
        
        summary['total_upstreams'] = len(upstream_matches)
        
        # 获取每个upstream的连接信息
        for upstream_name in upstream_matches:
            connection_info = estimate_upstream_connections(upstream_name)
            if 'error' not in connection_info:
                summary['total_connections'] += connection_info['total_connections']
                summary['total_active_connections'] += connection_info['active_connections']
                summary['total_max_connections'] += connection_info['max_connections']
                
                upstream_detail = {
                    'name': upstream_name,
                    'total_connections': connection_info['total_connections'],
                    'active_connections': connection_info['active_connections'],
                    'max_connections': connection_info['max_connections'],
                    'utilization_percentage': round(
                        (connection_info['total_connections'] / connection_info['max_connections']) * 100, 2
                    ) if connection_info['max_connections'] > 0 else 0
                }
                summary['upstreams_details'].append(upstream_detail)
        
    except Exception as e:
        logger.error(f"获取所有upstream连接汇总失败: {e}")
        summary['error'] = f"汇总失败: {e}"
    
    return summary
