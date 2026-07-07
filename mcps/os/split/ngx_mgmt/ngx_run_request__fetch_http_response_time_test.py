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


def fetch_http_response_time_test():
    """通过HTTP测试获取响应时间"""
    try:
        # 测试本地Nginx服务
        test_urls = [
            'http://localhost',  # NOSONAR
            'http://127.0.0.1',  # NOSONAR
            'http://localhost:80'  # NOSONAR
        ]

        response_times = []

        for url in test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # 转换为毫秒
                response_times.append(response_time)

                if len(response_times) >= 5:  # 最多测试5次
                    break

            except Exception as e:
                logger.warning(f'HTTP测试请求失败 {url}: {e}')
                continue

        if response_times:
            response_times.sort()
            n = len(response_times)

            return {
                'tp99': f"{response_times[int(n * 0.99)] if n > 1 else response_times[0]:.1f}",
                'tp95': f"{response_times[int(n * 0.95)] if n > 1 else response_times[0]:.1f}",
                'tp90': f"{response_times[int(n * 0.90)] if n > 1 else response_times[0]:.1f}",
                'avg_response_time': f"{sum(response_times) / n:.1f}",
                'min_response_time': f"{min(response_times):.1f}",
                'max_response_time': f"{max(response_times):.1f}"
            }

        return None

    except Exception as e:
        logger.error(f'HTTP响应时间测试失败: {e}')
        return None
