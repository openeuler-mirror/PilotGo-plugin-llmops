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


def fetch_access_log_status_statistics():
    """从访问日志获取状态码统计"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        status_codes = []

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取最近1000行日志
                    lines = f.readlines()[-1000:]

                    for line in lines:
                        # 解析状态码
                        match = re.search(r'"[^"]*"\s+(\d{3})\s+', line.strip())  # NOSONAR
                        if match:
                            status_code = int(match.group(1))
                            status_codes.append(status_code)

            except Exception as e:
                logger.warning(f'分析日志文件 {log_path} 失败: {e}')
                continue

        if not status_codes:
            return None

        # 统计各类状态码
        success_count = len([s for s in status_codes if 200 <= s < 300])
        redirect_count = len([s for s in status_codes if 300 <= s < 400])
        client_error_count = len([s for s in status_codes if 400 <= s < 500])
        server_error_count = len([s for s in status_codes if 500 <= s < 600])
        total_count = len(status_codes)

        return {
            'success_count': success_count,
            'redirect_count': redirect_count,
            'client_error_count': client_error_count,
            'server_error_count': server_error_count,
            'success_rate': f"{(success_count / total_count) * 100:.1f}" if total_count > 0 else "0.0"
        }

    except Exception as e:
        logger.error(f'分析访问日志状态码失败: {e}')
        return None
