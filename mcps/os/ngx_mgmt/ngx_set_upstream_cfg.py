#!/usr/bin/env python3
"""
Nginx上游服务配置设置工具
设置上游服务的负载均衡策略、超时时间、重试次数、熔断阈值等配置参数
"""

import os
import re
import logging
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_config')

def verify_nginx_installed() -> bool:
    """
    检查Nginx是否安装
    
    返回:
        bool: 是否安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception as e:
        logger.error(f"检查Nginx安装状态失败: {e}")
        return False

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

def locate_upstream_block(upstream_name: str, config_content: str) -> Tuple[Optional[str], int, int]:
    """
    查找上游服务配置块
    
    参数:
        upstream_name: 上游服务名称
        config_content: 配置文件内容
        
    返回:
        tuple: (配置块内容, 起始位置, 结束位置)
    """
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 匹配指定的upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
        match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        upstream_content = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        return upstream_content, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找上游服务配置块失败: {e}")
        return None, -1, -1

def analyze_existing_upstream_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析现有的上游服务配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 现有配置信息
    """
    settings = {
        'servers': [],
        'load_balancing': {},
        'timeout_settings': {},
        'retry_mechanism': {},
        'health_check': {},
        'other_configs': {}
    }
    
    try:
        # 解析服务器配置
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = re.finditer(server_pattern, upstream_content)  # NOSONAR
        
        for match in server_matches:
            server_config = match.group(1).strip()
            settings['servers'].append(server_config)
        
        # 解析负载均衡策略
        lb_methods = ['ip_hash', 'least_conn', 'hash', 'sticky']
        for method in lb_methods:
            if re.search(rf'\b{method}\b', upstream_content):  # NOSONAR
                settings['load_balancing']['method'] = method
                if method == 'hash':
                    hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
                    if hash_match:
                        settings['load_balancing']['hash_key'] = hash_match.group(1).strip()
        
        # 解析超时设置
        timeout_patterns = {
            'proxy_connect_timeout': r'proxy_connect_timeout\s+([^;]+);',
            'proxy_send_timeout': r'proxy_send_timeout\s+([^;]+);',
            'proxy_read_timeout': r'proxy_read_timeout\s+([^;]+);',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);'
        }
        
        for key, pattern in timeout_patterns.items():
            match = re.search(pattern, upstream_content)  # NOSONAR
            if match:
                settings['timeout_settings'][key] = match.group(1).strip()
        
        # 解析重试机制
        retry_patterns = {
            'proxy_next_upstream': r'proxy_next_upstream\s+([^;]+);',
            'proxy_next_upstream_timeout': r'proxy_next_upstream_timeout\s+([^;]+);',
            'proxy_next_upstream_tries': r'proxy_next_upstream_tries\s+([^;]+);'
        }
        
        for key, pattern in retry_patterns.items():
            match = re.search(pattern, upstream_content)  # NOSONAR
            if match:
                settings['retry_mechanism'][key] = match.group(1).strip()
        
        # 解析熔断阈值（服务器级别的）
        for server_config in settings['servers']:
            if 'max_fails=' in server_config:
                max_fails_match = re.search(r'max_fails=(\d+)', server_config)  # NOSONAR
                if max_fails_match:
                    settings['other_configs']['max_fails'] = max_fails_match.group(1)
            if 'fail_timeout=' in server_config:
                fail_timeout_match = re.search(r'fail_timeout=([^\s]+)', server_config)  # NOSONAR
                if fail_timeout_match:
                    settings['other_configs']['fail_timeout'] = fail_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析现有上游服务配置失败: {e}")
    
    return settings