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


def fetch_cache_disk_usage():
    """获取缓存磁盘使用情况"""
    stats = {
        'cache_size': 'N/A',
        'cache_max_size': 'N/A',
        'cache_path': 'N/A',
        'cache_levels': 'N/A',
        'cache_keys_zone': 'N/A',
        'cache_inactive': 'N/A'
    }
    
    try:
        # 获取缓存配置
        cache_config = fetch_nginx_cache_config()
        
        if cache_config['proxy_cache_path']:
            # 使用第一个缓存路径
            cache_info = cache_config['proxy_cache_path'][0]
            cache_path = cache_info['path']
            
            # 计算缓存目录大小
            cache_size = fetch_directory_size(cache_path)
            
            stats.update({
                'cache_path': cache_path,
                'cache_size': render_size(cache_size),
                'cache_max_size': cache_info['max_size'] if cache_info['max_size'] != 'N/A' else 'unlimited',
                'cache_levels': cache_info['levels'],
                'cache_keys_zone': f"{cache_info['zone_name']}:{cache_info['zone_size']}",
                'cache_inactive': cache_info['inactive']
            })
        
        elif cache_config['fastcgi_cache_path']:
            # 使用第一个 FastCGI 缓存路径
            cache_info = cache_config['fastcgi_cache_path'][0]
            cache_path = cache_info['path']
            
            # 计算缓存目录大小
            cache_size = fetch_directory_size(cache_path)
            
            stats.update({
                'cache_path': cache_path,
                'cache_size': render_size(cache_size),
                'cache_max_size': cache_info['max_size'] if cache_info['max_size'] != 'N/A' else 'unlimited',
                'cache_levels': cache_info['levels'],
                'cache_keys_zone': f"{cache_info['zone_name']}:{cache_info['zone_size']}",
                'cache_inactive': cache_info['inactive']
            })
        
        return stats
        
    except Exception as e:
        logger.error(f'获取缓存磁盘使用情况失败: {e}')
        return stats
