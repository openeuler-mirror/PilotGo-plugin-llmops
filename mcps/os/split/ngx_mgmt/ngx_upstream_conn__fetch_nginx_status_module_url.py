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


def fetch_nginx_status_module_url() -> Optional[str]:
    """
    获取Nginx状态模块URL
    
    返回:
        str: 状态模块URL，如果未配置返回None
    """
    try:
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        body = load_nginx_config(cfg_filepath)
        
        # 查找status模块配置
        status_pattern = r'location\s+/(\w+/)?status\s*\{[^}]+\}'  # NOSONAR
        status_matches = re.finditer(status_pattern, body, re.DOTALL)  # NOSONAR
        
        for match in status_matches:
            location_content = match.group(0)
            if 'stub_status' in location_content:
                # 获取监听的端口和地址
                server_pattern = r'listen\s+([^;]+);'  # NOSONAR
                server_matches = re.findall(server_pattern, body)  # NOSONAR
                
                for server_match in server_matches:
                    listen_config = server_match.strip()
                    port = listen_config.split(':')[1] if ':' in listen_config else listen_config
                    return f"http://127.0.0.1:{port}/status"  # NOSONAR
        
        # 常见状态模块URL
        common_urls = [
            "http://127.0.0.1:80/status",  # NOSONAR
            "http://127.0.0.1:8080/status",  # NOSONAR
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
