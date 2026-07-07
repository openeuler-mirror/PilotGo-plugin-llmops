#!/usr/bin/env python3

from datetime import datetime
from typing import Dict, Optional, List
import json
import logging
import os
import re
import subprocess
import time

import psutil
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_request')


def fetch_response_time_statistics():
    """获取响应时间统计"""
    stats = {
        'tp99': 'N/A',
        'tp95': 'N/A',
        'tp90': 'N/A',
        'avg_response_time': 'N/A',
        'min_response_time': 'N/A',
        'max_response_time': 'N/A'
    }

    try:
        # 尝试从访问日志分析响应时间
        log_analysis = examine_access_log_response_time()
        if log_analysis:
            stats.update(log_analysis)

        # 尝试通过HTTP请求测试获取响应时间
        http_test_stats = fetch_http_response_time_test()
        if http_test_stats and stats['avg_response_time'] == 'N/A':
            stats.update(http_test_stats)

        return stats

    except Exception as e:
        logger.error(f'获取响应时间统计失败: {e}')
        return stats
