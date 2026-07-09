#!/usr/bin/env python3
"""
Nginx上游服务器失败监控工具
获取上游服务器的失败请求数、失败率、熔断状态、重试次数等信息
"""

import os
import re
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_fail')

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
            # 解析配置文件路径
            config_match = re.search(r'nginx: the configuration file ([^\s]+)', output)  # NOSONAR
            if config_match:
                return config_match.group(1)
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None

def load_nginx_config(cfg_filepath: str) -> str:
    """
    读取Nginx配置文件内容
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 配置文件内容
    """
    try:
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Nginx配置文件失败: {e}")
        return ""

def fetch_upstream_configuration(upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    获取upstream配置信息
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: upstream配置信息
    """
    try:
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        body = load_nginx_config(cfg_filepath)
        
        # 查找指定的upstream块
        upstream_pattern = rf'upstream\s+{upstream_name}\s*{{([^}}]+)}}'  # NOSONAR
        upstream_match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not upstream_match:
            return None
        
        upstream_content = upstream_match.group(1)
        
        # 解析服务器配置
        servers = []
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = re.finditer(server_pattern, upstream_content)  # NOSONAR
        
        for match in server_matches:
            server_config = match.group(1).strip()
            server_info = analyze_server_config(server_config)
            servers.append(server_info)
        
        # 解析负载均衡策略
        lb_method = analyze_load_balancing_method(upstream_content)
        
        # 解析重试配置
        retry_config = analyze_retry_config(upstream_content)
        
        return {
            'name': upstream_name,
            'servers': servers,
            'load_balancing_method': lb_method,
            'retry_config': retry_config,
            'server_count': len(servers)
        }
        
    except Exception as e:
        logger.error(f"获取upstream配置失败 {upstream_name}: {e}")
        return None

def analyze_server_config(server_config: str) -> Dict[str, Any]:
    """
    解析服务器配置
    
    参数:
        server_config: 服务器配置字符串
        
    返回:
        dict: 服务器详细信息
    """
    server_info = {
        'address': 'unknown',
        'port': 80,
        'weight': 1,
        'max_fails': 1,
        'fail_timeout': '10s',
        'backup': False,
        'down': False,
        'max_conns': 0
    }
    
    try:
        # 解析地址和端口
        parts = server_config.split()
        if parts:
            address_part = parts[0]
            if ':' in address_part:
                addr_parts = address_part.split(':')
                server_info['address'] = addr_parts[0]
                server_info['port'] = int(addr_parts[1]) if addr_parts[1].isdigit() else 80
            else:
                server_info['address'] = address_part
        
        # 解析参数
        for part in parts[1:]:
            if part == 'backup':
                server_info['backup'] = True
            elif part == 'down':
                server_info['down'] = True
            elif part.startswith('weight='):
                server_info['weight'] = int(part.split('=')[1])
            elif part.startswith('max_fails='):
                server_info['max_fails'] = int(part.split('=')[1])
            elif part.startswith('fail_timeout='):
                server_info['fail_timeout'] = part.split('=')[1]
            elif part.startswith('max_conns='):
                server_info['max_conns'] = int(part.split('=')[1])
        
    except Exception as e:
        logger.error(f"解析服务器配置失败 {server_config}: {e}")
    
    return server_info

def analyze_load_balancing_method(upstream_content: str) -> str:
    """
    解析负载均衡策略
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        str: 负载均衡策略
    """
    lb_method = 'round-robin'  # 默认轮询
    
    try:
        if re.search(r'ip_hash', upstream_content):  # NOSONAR
            lb_method = 'ip_hash'
        elif re.search(r'least_conn', upstream_content):  # NOSONAR
            lb_method = 'least_conn'
        elif re.search(r'hash', upstream_content):  # NOSONAR
            hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
            if hash_match:
                lb_method = f"hash: {hash_match.group(1)}"
        elif re.search(r'fair', upstream_content):  # NOSONAR
            lb_method = 'fair'
        elif re.search(r'url_hash', upstream_content):  # NOSONAR
            lb_method = 'url_hash'
        
    except Exception as e:
        logger.error(f"解析负载均衡策略失败: {e}")
    
    return lb_method

def analyze_retry_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析重试配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 重试配置信息
    """
    retry_config = {
        'proxy_next_upstream': 'error timeout',
        'proxy_next_upstream_tries': 0,
        'proxy_next_upstream_timeout': '0s',
        'proxy_connect_timeout': '60s',
        'proxy_read_timeout': '60s',
        'proxy_send_timeout': '60s'
    }
    
    try:
        # 查找proxy_next_upstream配置
        next_upstream_match = re.search(r'proxy_next_upstream\s+([^;]+);', upstream_content)  # NOSONAR
        if next_upstream_match:
            retry_config['proxy_next_upstream'] = next_upstream_match.group(1)
        
        # 查找重试次数配置
        tries_match = re.search(r'proxy_next_upstream_tries\s+(\d+);', upstream_content)  # NOSONAR
        if tries_match:
            retry_config['proxy_next_upstream_tries'] = int(tries_match.group(1))
        
        # 查找重试超时配置
        timeout_match = re.search(r'proxy_next_upstream_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if timeout_match:
            retry_config['proxy_next_upstream_timeout'] = timeout_match.group(1)
        
        # 查找连接超时配置
        connect_timeout_match = re.search(r'proxy_connect_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if connect_timeout_match:
            retry_config['proxy_connect_timeout'] = connect_timeout_match.group(1)
        
        # 查找读取超时配置
        read_timeout_match = re.search(r'proxy_read_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if read_timeout_match:
            retry_config['proxy_read_timeout'] = read_timeout_match.group(1)
        
        # 查找发送超时配置
        send_timeout_match = re.search(r'proxy_send_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if send_timeout_match:
            retry_config['proxy_send_timeout'] = send_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析重试配置失败: {e}")
    
    return retry_config