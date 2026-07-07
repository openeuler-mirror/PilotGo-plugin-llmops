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


def fetch_stub_status_stats(status_url):
    """从 stub_status 页面获取统计信息"""
    stats = {}
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            body = response.text.strip()
            
            # 解析 stub_status 输出
            # Active connections: 291
            active_match = re.search(r'Active connections:\s*(\d+)', body)  # NOSONAR
            if active_match:
                stats['active_connections'] = int(active_match.group(1))
            
            # server accepts handled requests
            # 16630948 16630948 31070465
            server_match = re.search(  # NOSONAR
                r'server\s+accepts\s+handled\s+requests\s*\n\s*(\d+)\s+(\d+)\s+(\d+)',  # NOSONAR 
                body  # NOSONAR
                )  # NOSONAR
            if server_match:
                stats['total_connections'] = int(server_match.group(1))
                stats['total_handshakes'] = int(server_match.group(2))
                stats['total_requests'] = int(server_match.group(3))
            
            # Reading: 6 Writing: 179 Waiting: 106
            reading_match = re.search(r'Reading:\s*(\d+)', body)  # NOSONAR
            writing_match = re.search(r'Writing:\s*(\d+)', body)  # NOSONAR
            waiting_match = re.search(r'Waiting:\s*(\d+)', body)  # NOSONAR
            
            if reading_match:
                stats['reading_connections'] = int(reading_match.group(1))
            if writing_match:
                stats['writing_connections'] = int(writing_match.group(1))
            if waiting_match:
                stats['waiting_connections'] = int(waiting_match.group(1))
                
    except Exception as e:
        logger.error(f'获取 stub_status 统计失败: {e}')
    
    return stats
