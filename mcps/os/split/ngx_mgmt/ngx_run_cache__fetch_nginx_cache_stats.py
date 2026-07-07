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
