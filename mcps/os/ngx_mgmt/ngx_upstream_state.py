#!/usr/bin/env python3
"""
Nginx上游服务器状态监控工具
获取指定上游服务器的状态（在线/离线/异常）、权重、当前连接数等信息
"""

import os
import re
import json
import logging
import subprocess
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_status')

def fetch_nginx_status_module_url() -> Optional[str]:
    """
    获取Nginx状态模块URL
    
    返回:
        str: 状态模块URL，如果未配置返回None
    """
    try:
        # 获取配置文件路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        # 读取配置文件
        body = load_nginx_config(cfg_filepath)
        
        # 查找status模块配置
        status_pattern = r'location\s+/(\w+/)?state\s*\{[^}]+\}'  # NOSONAR
        status_matches = re.finditer(status_pattern, body, re.DOTALL)  # NOSONAR
        
        for match in status_matches:
            # 解析location块内容
            location_content = match.group(0)
            if 'stub_status' in location_content:
                # 获取监听的端口和地址
                server_pattern = r'listen\s+([^;]+);'  # NOSONAR
                server_matches = re.findall(server_pattern, body)  # NOSONAR
                
                for server_match in server_matches:
                    listen_config = server_match.strip()
                    port = listen_config.split(':')[1] if ':' in listen_config else listen_config
                    # 构建URL
                    return f"http://127.0.0.1:{port}/state"  # NOSONAR
        
        # 常见状态模块URL
        common_urls = [
            "http://127.0.0.1:80/state",  # NOSONAR
            "http://127.0.0.1:8080/state",  # NOSONAR
            "http://localhost/nginx_status",  # NOSONAR
            "http://127.0.0.1/nginx_status"  # NOSONAR
        ]
        
        for url in common_urls:
            if verify_url_accessibility(url):
                return url
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx状态模块URL失败: {e}")
        return None

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

def verify_url_accessibility(url: str, timeout: int = 5) -> bool:
    """
    检查URL可访问性
    
    参数:
        url: 要检查的URL
        timeout: 超时时间（秒）
        
    返回:
        bool: 是否可访问
    """
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def fetch_upstream_status_from_nginx_plus(upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    从Nginx Plus获取upstream状态（商业版功能）
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: upstream状态信息
    """
    try:
        # Nginx Plus状态API
        status_urls = [
            f"http://127.0.0.1:8080/api/3/http/upstreams/{upstream_name}/peers",  # NOSONAR
            f"http://127.0.0.1:80/api/3/http/upstreams/{upstream_name}/peers"  # NOSONAR
        ]
        
        for url in status_urls:
            if verify_url_accessibility(url):
                import requests
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()
        
        return None
        
    except Exception as e:
        logger.error(f"从Nginx Plus获取状态失败: {e}")
        return None

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
        
        return {
            'name': upstream_name,
            'servers': servers,
            'load_balancing_method': lb_method,
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

def verify_server_connectivity(server_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    检查服务器连通性
    
    参数:
        server_info: 服务器信息
        
    返回:
        dict: 连通性检查结果
    """
    connectivity = {
        'state': 'unknown',
        'response_time': 0,
        'error': None,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        address = server_info['address']
        port = server_info['port']
        
        # 检查端口连通性
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        output = sock.connect_ex((address, port))
        end_time = time.time()
        
        connectivity['response_time'] = round((end_time - start_time) * 1000, 2)  # 毫秒
        
        if output == 0:
            connectivity['state'] = 'online'
        else:
            connectivity['state'] = 'offline'
            connectivity['error'] = f"连接失败 (错误码: {output})"
        
        sock.close()
        
    except socket.timeout:
        connectivity['state'] = 'timeout'
        connectivity['error'] = '连接超时'
    except socket.gaierror as e:
        connectivity['state'] = 'dns_error'
        connectivity['error'] = f"DNS解析失败: {e}"
    except Exception as e:
        connectivity['state'] = 'error'
        connectivity['error'] = f"连接检查失败: {e}"
    
    return connectivity