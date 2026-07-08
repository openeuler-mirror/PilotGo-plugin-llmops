#!/usr/bin/env python3
"""
Nginx上游服务配置工具
获取上游服务的详细配置信息，包括负载均衡策略、超时时间、重试机制等
"""

import os
import re
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_config')

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

def locate_upstream_config(upstream_name: str, config_content: str, config_file: str) -> Optional[Dict[str, Any]]:
    """
    查找指定上游服务的配置
    
    参数:
        upstream_name: 上游服务名称
        config_content: 配置文件内容
        config_file: 配置文件路径
        
    返回:
        dict: 上游服务配置信息
    """
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 匹配指定的upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
        match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not match:
            return None
        
        upstream_content = match.group(1).strip()
        
        # 解析详细配置
        cfg_state = analyze_detailed_upstream_config(upstream_name, upstream_content, config_file)
        cfg_state['line_number'] = fetch_line_number(config_content, match.start())
        
        return cfg_state
        
    except Exception as e:
        logger.error(f"查找上游服务配置失败: {e}")
        return None

def analyze_detailed_upstream_config(upstream_name: str, upstream_content: str, config_file: str) -> Dict[str, Any]:
    """
    解析上游服务的详细配置信息
    
    参数:
        upstream_name: 上游服务名称
        upstream_content: upstream块内容
        config_file: 配置文件路径
        
    返回:
        dict: 详细配置信息
    """
    cfg_state = {
        'name': upstream_name,
        'config_file': config_file,
        'servers': [],
        'load_balancing': {},
        'timeout_settings': {},
        'retry_mechanism': {},
        'health_check': {},
        'other_configs': {},
        'parsed_at': datetime.now().isoformat()
    }
    
    try:
        # 解析服务器配置
        cfg_state['servers'] = analyze_server_configs(upstream_content)
        
        # 解析负载均衡策略
        cfg_state['load_balancing'] = analyze_load_balancing_config(upstream_content)
        
        # 解析超时设置
        cfg_state['timeout_settings'] = analyze_timeout_config(upstream_content)
        
        # 解析重试机制
        cfg_state['retry_mechanism'] = analyze_retry_config(upstream_content)
        
        # 解析健康检查配置
        cfg_state['health_check'] = analyze_health_check_config(upstream_content)
        
        # 解析其他配置参数
        cfg_state['other_configs'] = analyze_other_configs(upstream_content)
        
    except Exception as e:
        logger.error(f"解析上游服务详细配置失败: {e}")
    
    return cfg_state

def analyze_server_configs(upstream_content: str) -> List[Dict[str, Any]]:
    """
    解析服务器详细配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        list: 服务器配置列表
    """
    servers = []
    
    try:
        # 匹配server指令
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = re.finditer(server_pattern, upstream_content)  # NOSONAR
        
        for match in server_matches:
            server_config = match.group(1).strip()
            server_info = analyze_individual_server_config(server_config)
            servers.append(server_info)
        
    except Exception as e:
        logger.error(f"解析服务器配置失败: {e}")
    
    return servers

def analyze_individual_server_config(server_config: str) -> Dict[str, Any]:
    """
    解析单个服务器的详细配置
    
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
        'max_conns': 0,
        'slow_start': '0s',
        'route': None,
        'service': None
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
        
        # 解析详细参数
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
            elif part.startswith('slow_start='):
                server_info['slow_start'] = part.split('=')[1]
            elif part.startswith('route='):
                server_info['route'] = part.split('=')[1]
            elif part.startswith('service='):
                server_info['service'] = part.split('=')[1]
        
    except Exception as e:
        logger.error(f"解析单个服务器配置失败: {e}")
    
    return server_info

def analyze_load_balancing_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析负载均衡策略配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 负载均衡配置信息
    """
    lb_config = {
        'method': 'round-robin',  # 默认轮询
        'hash_key': None,
        'consistent_hashing': False,
        'least_conn': False,
        'ip_hash': False,
        'sticky': False
    }
    
    try:
        # 检查负载均衡方法
        if re.search(r'ip_hash', upstream_content):  # NOSONAR
            lb_config['method'] = 'ip_hash'
            lb_config['ip_hash'] = True
        elif re.search(r'least_conn', upstream_content):  # NOSONAR
            lb_config['method'] = 'least_conn'
            lb_config['least_conn'] = True
        elif re.search(r'hash\s+', upstream_content):  # NOSONAR
            lb_config['method'] = 'hash'
            hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
            if hash_match:
                lb_config['hash_key'] = hash_match.group(1).strip()
                if 'consistent' in upstream_content:
                    lb_config['consistent_hashing'] = True
        elif re.search(r'sticky', upstream_content):  # NOSONAR
            lb_config['method'] = 'sticky'
            lb_config['sticky'] = True
        
    except Exception as e:
        logger.error(f"解析负载均衡配置失败: {e}")
    
    return lb_config

def analyze_timeout_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析超时时间配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 超时配置信息
    """
    timeout_config = {
        'connect_timeout': None,
        'send_timeout': None,
        'read_timeout': None,
        'keepalive_timeout': None,
        'proxy_connect_timeout': None,
        'proxy_send_timeout': None,
        'proxy_read_timeout': None
    }
    
    try:
        # 解析各种超时设置
        timeout_patterns = {
            'connect_timeout': r'proxy_connect_timeout\s+([^;]+);',
            'send_timeout': r'proxy_send_timeout\s+([^;]+);',
            'read_timeout': r'proxy_read_timeout\s+([^;]+);',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);'
        }
        
        for key, pattern in timeout_patterns.items():
            match = re.search(pattern, upstream_content)  # NOSONAR
            if match:
                timeout_config[key] = match.group(1).strip()
        
    except Exception as e:
        logger.error(f"解析超时配置失败: {e}")
    
    return timeout_config