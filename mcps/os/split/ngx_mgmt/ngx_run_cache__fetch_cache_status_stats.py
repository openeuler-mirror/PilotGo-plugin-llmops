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


def fetch_cache_status_stats():
    """获取缓存状态统计"""
    stats = {
        'hit_ratio': 'N/A',
        'hits': 'N/A',
        'misses': 'N/A',
        'expired': 'N/A',
        'stale': 'N/A',
        'updating': 'N/A',
        'revalidated': 'N/A',
        'scarce': 'N/A'
    }
    
    try:
        # 尝试从 stub_status 模块获取缓存统计
        stub_info = fetch_nginx_stub_status_info()
        if stub_info and 'location' in stub_info:
            stub_stats = fetch_stub_status_stats(stub_info['location'])
            if stub_stats:
                # 从 stub_status 获取基本连接信息
                stats.update({
                    'active_connections': stub_stats.get('active_connections', 'N/A'),
                    'total_requests': stub_stats.get('total_requests', 'N/A')
                })
        
        # 尝试从 Nginx Plus API 获取缓存统计
        plus_stats = fetch_nginx_plus_cache_stats()
        if plus_stats:
            stats.update(plus_stats)
        
        # 计算命中率（如果有足够的数据）
        if stats['hits'] != 'N/A' and stats['misses'] != 'N/A':
            total = stats['hits'] + stats['misses']
            if total > 0:
                stats['hit_ratio'] = f"{(stats['hits'] / total) * 100:.2f}%"
        
        return stats
        
    except Exception as e:
        logger.error(f'获取缓存状态统计失败: {e}')
        return stats
