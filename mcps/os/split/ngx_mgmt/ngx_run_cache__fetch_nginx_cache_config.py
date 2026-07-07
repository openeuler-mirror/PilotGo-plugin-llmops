#!/usr/bin/env python3

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


def fetch_nginx_cache_config():
    """获取Nginx缓存配置信息"""
    settings = {
        'proxy_cache_path': [],
        'fastcgi_cache_path': [],
        'proxy_cache': [],
        'fastcgi_cache': [],
        'cache_zones': {}
    }
    
    try:
        # 获取Nginx配置文件内容
        config_content = fetch_nginx_config_content()
        
        if not config_content:
            return settings
        
        # 解析 proxy_cache_path 指令
        proxy_cache_paths = re.findall(  # NOSONAR
            r'proxy_cache_path\s+(\S+)\s+keys_zone=([^:]+):(\d+)(?:\s+inactive=([^;\s]+))?(?:\s+max_size=([^;\s]+))?(?:\s+use_temp_path=([^;\s]+))?(?:\s+levels=([^;\s]+))?',
            config_content, re.IGNORECASE  # NOSONAR
        )
        
        for path_info in proxy_cache_paths:
            cache_info = {
                'path': path_info[0],
                'zone_name': path_info[1],
                'zone_size': f"{path_info[2]}m",
                'inactive': path_info[3] if path_info[3] else '10m',
                'max_size': path_info[4] if path_info[4] else 'N/A',
                'use_temp_path': path_info[5] if path_info[5] else 'on',
                'levels': path_info[6] if path_info[6] else '1:2',
                'type': 'proxy'
            }
            settings['proxy_cache_path'].append(cache_info)
            settings['cache_zones'][cache_info['zone_name']] = cache_info
        
        # 解析 fastcgi_cache_path 指令
        fastcgi_cache_paths = re.findall(  # NOSONAR
            r'fastcgi_cache_path\s+(\S+)\s+keys_zone=([^:]+):(\d+)(?:\s+inactive=([^;\s]+))?(?:\s+max_size=([^;\s]+))?(?:\s+use_temp_path=([^;\s]+))?(?:\s+levels=([^;\s]+))?',
            config_content, re.IGNORECASE  # NOSONAR
        )
        
        for path_info in fastcgi_cache_paths:
            cache_info = {
                'path': path_info[0],
                'zone_name': path_info[1],
                'zone_size': f"{path_info[2]}m",
                'inactive': path_info[3] if path_info[3] else '10m',
                'max_size': path_info[4] if path_info[4] else 'N/A',
                'use_temp_path': path_info[5] if path_info[5] else 'on',
                'levels': path_info[6] if path_info[6] else '1:2',
                'type': 'fastcgi'
            }
            settings['fastcgi_cache_path'].append(cache_info)
            settings['cache_zones'][cache_info['zone_name']] = cache_info
        
        # 解析 proxy_cache 指令
        proxy_caches = re.findall(  # NOSONAR
            r'proxy_cache\s+([^;\s]+)',
            config_content, re.IGNORECASE  # NOSONAR
        )
        settings['proxy_cache'] = sorted(set(proxy_caches))
        
        # 解析 fastcgi_cache 指令
        fastcgi_caches = re.findall(  # NOSONAR
            r'fastcgi_cache\s+([^;\s]+)',
            config_content, re.IGNORECASE  # NOSONAR
        )
        settings['fastcgi_cache'] = sorted(set(fastcgi_caches))
        
        return settings
        
    except Exception as e:
        logger.error(f'获取缓存配置失败: {e}')
        return settings
