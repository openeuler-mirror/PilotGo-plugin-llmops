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


def fetch_stub_status_stats(status_url):
    """从stub_status页面获取统计信息"""
    stats = {}
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            body = response.text.strip()

            # 解析stub_status输出
            # server accepts handled requests
            # 16630948 16630948 31070465
            server_match = re.search(r'server\s+accepts\s+handled\s+requests\s*\n\s*(\d+)\s+(\d+)\s+(\d+)', body)  # NOSONAR
            if server_match:
                stats['total_requests'] = int(server_match.group(3))  # 第三个数字是总请求数
                stats['handled_requests'] = int(server_match.group(2))  # 第二个数字是处理的连接数

    except Exception as e:
        logger.error(f'获取stub_status统计失败: {e}')

    return stats
