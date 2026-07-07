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


def fetch_stub_status_info():
    """获取stub_status模块信息"""
    try:
        # 检查nginx配置中是否启用了stub_status
        output = subprocess.run(['nginx', '-T'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode in [0, 1]:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 查找stub_status配置
            stub_status_matches = re.findall(r'location\s+([^/]*)/nginx_status\s*{[^}]*stub_status', output, re.IGNORECASE | re.DOTALL)  # NOSONAR
            if not stub_status_matches:
                stub_status_matches = re.findall(r'location\s+([^/]*)/status\s*{[^}]*stub_status', output, re.IGNORECASE | re.DOTALL)  # NOSONAR

            if stub_status_matches:
                location = stub_status_matches[0].strip() if stub_status_matches[0].strip() else ''
                return {
                    'enabled': True,
                    'location': f"{location}/nginx_status" if location else "/nginx_status",
                    'message': 'stub_status模块已配置'
                }

        # 尝试常见的状态页面URL
        common_urls = [
            'http://localhost/nginx_status',  # NOSONAR
            'http://127.0.0.1/nginx_status',  # NOSONAR
            'http://localhost/status',  # NOSONAR
            'http://127.0.0.1/status'  # NOSONAR
        ]

        for url in common_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200 and 'Active connections' in response.text:
                    return {
                        'enabled': True,
                        'location': url,
                        'message': f'stub_status模块可通过 {url} 访问'
                    }
            except Exception:
                continue

        return {'enabled': False, 'message': 'stub_status模块未启用或无法访问'}

    except Exception as e:
        logger.error(f'获取stub_status信息失败: {e}')
        return {'enabled': False, 'message': f'检测失败: {e}'}
