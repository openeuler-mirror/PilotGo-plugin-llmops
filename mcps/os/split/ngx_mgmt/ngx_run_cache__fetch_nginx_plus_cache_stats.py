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


def fetch_nginx_plus_cache_stats():
    """获取 Nginx Plus 缓存统计（如果可用）"""
    stats = {}
    try:
        # 尝试访问 Nginx Plus API
        api_urls = [
            "http://localhost/api/3/http/caches",  # NOSONAR
            "http://localhost/api/2/http/caches",  # NOSONAR
            "http://127.0.0.1/api/3/http/caches",  # NOSONAR
            "http://127.0.0.1/api/2/http/caches"  # NOSONAR
        ]
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    cache_data = response.json()
                    
                    # 汇总所有缓存区的统计
                    total_hits = 0
                    total_misses = 0
                    total_expired = 0
                    total_stale = 0
                    total_updating = 0
                    total_revalidated = 0
                    total_scarce = 0
                    
                    for cache_name, cache_info in cache_data.items():
                        if 'hit' in cache_info:
                            total_hits += cache_info['hit']
                        if 'miss' in cache_info:
                            total_misses += cache_info['miss']
                        if 'expired' in cache_info:
                            total_expired += cache_info['expired']
                        if 'stale' in cache_info:
                            total_stale += cache_info['stale']
                        if 'updating' in cache_info:
                            total_updating += cache_info['updating']
                        if 'revalidated' in cache_info:
                            total_revalidated += cache_info['revalidated']
                        if 'scarce' in cache_info:
                            total_scarce += cache_info['scarce']
                    
                    stats = {
                        'hits': total_hits,
                        'misses': total_misses,
                        'expired': total_expired,
                        'stale': total_stale,
                        'updating': total_updating,
                        'revalidated': total_revalidated,
                        'scarce': total_scarce
                    }
                    break
                    
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
                
    except Exception as e:
        logger.error(f'获取 Nginx Plus 缓存统计失败: {e}')
    
    return stats
