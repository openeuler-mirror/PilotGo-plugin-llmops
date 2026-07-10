#!/usr/bin/env python3
"""
Nginx运行时连接限制管理工具
设置最大连接数、单IP最大连接数、连接队列长度等连接限制参数
"""

import os
import re
import json
import logging
import subprocess
import shutil
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, fetch_nginx_config_path, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_connect_limit')

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
    读取 Nginx 配置文件内容
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 配置文件内容
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"load_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return ""
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Nginx配置文件失败: {e}")
        return ""

def fetch_current_connection_settings(config_content: str) -> Dict[str, Any]:
    """
    获取当前连接限制设置
    
    参数:
        config_content: 配置文件内容
        
    返回:
        dict: 当前连接设置信息
    """
    settings = {
        'worker_connections': 512,  # 默认值
        'worker_rlimit_nofile': None,
        'multi_accept': 'off',
        'accept_mutex': 'on',
        'accept_mutex_delay': '500ms',
        'listen_backlog': 511,
        'keepalive_timeout': '75s',
        'keepalive_requests': 100,
        'client_max_body_size': '1m',
        'client_body_timeout': '60s',
        'client_header_timeout': '60s',
        'send_timeout': '60s',
        'limit_conn_zone': {},
        'limit_conn': {},
        'limit_req_zone': {},
        'limit_req': {}
    }
    
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 解析events块中的连接设置
        events_pattern = r'events\s*\{([^}]+)\}'  # NOSONAR
        events_match = re.search(events_pattern, body, re.DOTALL)  # NOSONAR
        
        if events_match:
            events_content = events_match.group(1)
            
            # 解析worker_connections
            worker_conn_match = re.search(r'worker_connections\s+(\d+);', events_content)  # NOSONAR
            if worker_conn_match:
                settings['worker_connections'] = int(worker_conn_match.group(1))
            
            # 解析其他events设置
            events_settings = {
                'multi_accept': r'multi_accept\s+(\w+);',
                'accept_mutex': r'accept_mutex\s+(\w+);',
                'accept_mutex_delay': r'accept_mutex_delay\s+([^;]+);',
                'use': r'use\s+([^;]+);'
            }
            
            for key, pattern in events_settings.items():
                match = re.search(pattern, events_content)  # NOSONAR
                if match:
                    settings[key] = match.group(1).strip()
        
        # 解析主配置中的连接相关设置
        main_settings = {
            'worker_rlimit_nofile': r'worker_rlimit_nofile\s+(\d+);',
            'listen_backlog': r'listen\s+[^;]+backlog=(\d+)[^;]*;',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);',
            'keepalive_requests': r'keepalive_requests\s+(\d+);',
            'client_max_body_size': r'client_max_body_size\s+([^;]+);',
            'client_body_timeout': r'client_body_timeout\s+([^;]+);',
            'client_header_timeout': r'client_header_timeout\s+([^;]+);',
            'send_timeout': r'send_timeout\s+([^;]+);'
        }
        
        for key, pattern in main_settings.items():
            match = re.search(pattern, body)  # NOSONAR
            if match:
                if key in ['keepalive_requests']:
                    settings[key] = int(match.group(1))
                elif key in ['listen_backlog']:
                    settings[key] = int(match.group(1))
                else:
                    settings[key] = match.group(1).strip()
        
        # 解析连接限制配置
        settings.update(analyze_connection_limits(body))
        
    except Exception as e:
        logger.error(f"获取当前连接设置失败: {e}")
    
    return settings