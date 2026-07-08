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


def fetch_nginx_upstream_connection(upstream_name: str = "") -> str:
    """
    获取Nginx上游服务连接数信息
    
    参数:
        upstream_name: upstream名称（可选，为空时获取所有upstream连接数汇总）
        
    返回:
        str: JSON格式的上游服务连接数信息
    """
    try:
        # 检查Nginx是否运行
        nginx_running = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                nginx_running = True
                break
        
        if not nginx_running:
            return json.dumps({
                'status': 'error',
                'message': 'Nginx服务未运行',
                'suggestion': '请先启动Nginx服务',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 根据是否指定upstream_name返回不同信息
        if upstream_name:
            # 获取指定upstream的连接信息
            connection_info = estimate_upstream_connections(upstream_name)
            connection_analysis = fetch_upstream_connection_analysis(upstream_name)
            
            output = {
                'status': 'success',
                'upstream_name': upstream_name,
                'connection_info': connection_info,
                'connection_analysis': connection_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
            if 'error' in connection_info:
                output['status'] = 'error'
                output['message'] = connection_info['error']
            
        else:
            # 获取所有upstream的连接汇总
            summary = fetch_all_upstreams_connection_summary()
            output = {
                'status': 'success',
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            }
            
            if 'error' in summary:
                output['status'] = 'error'
                output['message'] = summary['error']
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取Nginx上游连接数失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'获取连接数失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
