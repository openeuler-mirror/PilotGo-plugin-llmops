#!/usr/bin/env python3
"""
Nginx日志配置信息获取工具
获取日志切割规则、保留天数、日志级别、自定义日志格式等配置信息
"""

import os
import re
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_config')

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

def analyze_nginx_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 解析后的配置信息
    """
    settings = {
        'main_config': {},
        'http_config': {},
        'server_configs': [],
        'include_files': []
    }
    
    try:
        if not os.path.exists(cfg_filepath):
            logger.error(f"配置文件不存在: {cfg_filepath}")
            return settings
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析include文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        for include in includes:
            include_path = include.strip().strip('"\'')
            if not os.path.isabs(include_path):
                include_path = os.path.join(os.path.dirname(cfg_filepath), include_path)
            settings['include_files'].append(include_path)
        
        # 解析http块
        http_pattern = r'http\s*\{([^}]+)\}'  # NOSONAR
        http_match = re.search(http_pattern, body, re.DOTALL)  # NOSONAR
        if http_match:
            http_content = http_match.group(1)
            settings['http_config'] = analyze_config_block(http_content)
        
        # 解析server块
        server_pattern = r'server\s*\{([^}]+)\}'  # NOSONAR
        server_matches = re.finditer(server_pattern, body, re.DOTALL)  # NOSONAR
        for match in server_matches:
            server_content = match.group(1)
            server_config = analyze_config_block(server_content)
            settings['server_configs'].append(server_config)
        
        # 解析主配置
        main_content = re.sub(r'http\s*\{[^}]+\}', '', body, flags=re.DOTALL)  # NOSONAR
        main_content = re.sub(r'server\s*\{[^}]+\}', '', main_content, flags=re.DOTALL)  # NOSONAR
        settings['main_config'] = analyze_config_block(main_content)
        
    except Exception as e:
        logger.error(f"解析Nginx配置文件失败: {e}")
    
    return settings