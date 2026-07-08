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


def estimate_upstream_connections(upstream_name: str) -> Dict[str, Any]:
    """
    估算upstream连接数
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: 连接数估算信息
    """
    connection_estimate = {
        'upstream_name': upstream_name,
        'total_connections': 0,
        'active_connections': 0,
        'max_connections': 0,
        'connection_distribution': [],
        'estimation_method': 'calculated',
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取upstream配置
        upstream_config = fetch_upstream_configuration(upstream_name)
        if not upstream_config:
            connection_estimate['error'] = f"无法获取upstream配置: {upstream_name}"
            return connection_estimate
        
        # 获取Nginx状态信息
        nginx_status = fetch_nginx_status_info()
        process_connections = fetch_nginx_process_connections()
        
        # 计算总连接数
        if nginx_status:
            connection_estimate['total_connections'] = nginx_status['active_connections']
            connection_estimate['active_connections'] = nginx_status['active_connections'] - nginx_status['waiting']
        else:
            connection_estimate['total_connections'] = process_connections['total_connections']
            connection_estimate['active_connections'] = process_connections['active_connections']
        
        # 计算每个服务器的连接数分布
        total_weight = sum(server['weight'] for server in upstream_config['servers'] 
                          if not server['down'])
        
        if total_weight > 0:
            for server in upstream_config['servers']:
                if server['down']:
                    continue
                
                weight_ratio = server['weight'] / total_weight
                server_connections = {
                    'server_address': f"{server['address']}:{server['port']}",
                    'weight': server['weight'],
                    'estimated_connections': int(connection_estimate['total_connections'] * weight_ratio),
                    'max_connections': server.get('max_conns', 0),
                    'status': 'active' if not server.get('down', False) else 'down'
                }
                
                connection_estimate['connection_distribution'].append(server_connections)
                connection_estimate['max_connections'] += server_connections['max_connections']
        
        # 如果没有配置最大连接数，使用默认值
        if connection_estimate['max_connections'] == 0:
            connection_estimate['max_connections'] = len(upstream_config['servers']) * 1000  # 默认每个服务器1000连接
        
    except Exception as e:
        logger.error(f"估算upstream连接数失败 {upstream_name}: {e}")
        connection_estimate['error'] = f"估算失败: {e}"
    
    return connection_estimate
