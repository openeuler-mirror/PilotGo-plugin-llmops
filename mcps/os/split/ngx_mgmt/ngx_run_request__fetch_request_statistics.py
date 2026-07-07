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


def fetch_request_statistics():
    """获取请求统计信息"""
    stats = {
        'total_requests': 'N/A',
        'qps': 'N/A',
        'requests_per_minute': 'N/A',
        'requests_per_hour': 'N/A',
        'handled_requests': 'N/A',
        'dropped_requests': 'N/A'
    }

    try:
        # 首先尝试通过stub_status获取
        stub_info = fetch_stub_status_info()
        if stub_info['enabled']:
            stub_stats = fetch_stub_status_stats(stub_info['location'])
            if stub_stats.get('total_requests'):
                stats['total_requests'] = stub_stats['total_requests']
                stats['handled_requests'] = stub_stats.get('handled_requests', 'N/A')

                # 计算QPS
                uptime = fetch_nginx_uptime()
                if uptime > 0 and stats['total_requests'] != 'N/A':
                    qps = stats['total_requests'] / uptime
                    stats['qps'] = f"{qps:.2f}"
                    stats['requests_per_minute'] = f"{qps * 60:.0f}"
                    stats['requests_per_hour'] = f"{qps * 3600:.0f}"

        # 尝试从访问日志获取更详细的统计
        log_stats = fetch_access_log_statistics()
        if log_stats:
            # 如果stub_status没有数据，使用日志数据
            if stats['total_requests'] == 'N/A' and log_stats.get('total_requests'):
                stats['total_requests'] = log_stats['total_requests']
                if log_stats.get('qps'):
                    stats['qps'] = log_stats['qps']

        # 计算丢弃的请求数
        if stats['handled_requests'] != 'N/A' and stats['total_requests'] != 'N/A':
            stats['dropped_requests'] = max(0, stats['total_requests'] - stats['handled_requests'])

        return stats

    except Exception as e:
        logger.error(f'获取请求统计失败: {e}')
        return stats
