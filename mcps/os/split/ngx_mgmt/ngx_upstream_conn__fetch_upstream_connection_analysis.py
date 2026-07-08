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


def fetch_upstream_connection_analysis(upstream_name: str) -> Dict[str, Any]:
    """
    分析upstream连接状态
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: 连接状态分析
    """
    analysis = {
        'upstream_name': upstream_name,
        'connection_health': 'unknown',
        'utilization_percentage': 0,
        'recommendations': [],
        'alerts': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取连接数估算
        connection_estimate = estimate_upstream_connections(upstream_name)
        
        if 'error' in connection_estimate:
            analysis['error'] = connection_estimate['error']
            return analysis
        
        # 计算利用率
        if connection_estimate['max_connections'] > 0:
            analysis['utilization_percentage'] = round(
                (connection_estimate['total_connections'] / connection_estimate['max_connections']) * 100, 2
            )
        
        # 判断连接健康状态
        if analysis['utilization_percentage'] > 90:
            analysis['connection_health'] = 'critical'
            analysis['alerts'].append('连接数利用率超过90%，接近最大限制')
        elif analysis['utilization_percentage'] > 70:
            analysis['connection_health'] = 'warning'
            analysis['alerts'].append('连接数利用率超过70%，需要关注')
        else:
            analysis['connection_health'] = 'healthy'
        
        # 生成建议
        if analysis['utilization_percentage'] > 80:
            analysis['recommendations'].append('考虑增加服务器数量或调整连接限制')
        
        if any(server['max_connections'] == 0 for server in connection_estimate['connection_distribution']):
            analysis['recommendations'].append('建议为服务器配置max_conns参数以限制连接数')
        
        # 检查连接分布是否均衡
        if len(connection_estimate['connection_distribution']) > 1:
            connections = [s['estimated_connections'] for s in connection_estimate['connection_distribution']]
            max_conn = max(connections)
            min_conn = min(connections)
            
            if max_conn > min_conn * 3:  # 最大连接数超过最小连接数的3倍
                analysis['recommendations'].append('连接分布不均衡，建议检查负载均衡配置')
        
    except Exception as e:
        logger.error(f"分析upstream连接状态失败: {e}")
        analysis['error'] = f"分析失败: {e}"
    
    return analysis
