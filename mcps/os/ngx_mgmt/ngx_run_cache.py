#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nginx 缓存监控工具
用于获取Nginx缓存的命中率、命中/失效/过期数、缓存占用空间、缓存配置规则等信息
"""

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_nginx_cache_stats():
    """获取Nginx缓存统计信息"""
    cache_stats = {
        'hit_ratio': 'N/A',
        'hits': 'N/A',
        'misses': 'N/A',
        'expired': 'N/A',
        'stale': 'N/A',
        'updating': 'N/A',
        'revalidated': 'N/A',
        'scarce': 'N/A',
        'cache_size': 'N/A',
        'cache_max_size': 'N/A',
        'cache_keys_zone': 'N/A',
        'cache_path': 'N/A',
        'cache_levels': 'N/A',
        'cache_inactive': 'N/A',
        'cache_config': {}
    }
    
    try:
        # 获取Nginx配置信息
        cache_config = fetch_nginx_cache_config()
        cache_stats['cache_config'] = cache_config
        
        # 获取缓存状态信息
        status_stats = fetch_cache_status_stats()
        cache_stats.update(status_stats)
        
        # 获取缓存占用空间
        disk_stats = fetch_cache_disk_usage()
        cache_stats.update(disk_stats)
        
        return cache_stats
        
    except Exception as e:
        logger.error(f'获取缓存统计失败: {e}')
        return cache_stats


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