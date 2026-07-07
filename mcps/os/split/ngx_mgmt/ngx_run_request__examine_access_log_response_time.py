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


def examine_access_log_response_time():
    """分析访问日志中的响应时间"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        response_times = []
        status_codes = []

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取最近1000行日志
                    lines = f.readlines()[-1000:]

                    for line in lines:
                        # 解析Nginx访问日志格式
                        # 常见格式: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" $request_time
                        match = re.search(r'"[^"]*"\s+(\d{3})\s+\d+\s+"[^"]*"\s+"[^"]*"(?:\s+"[^"]*")?\s+([\d.]+)$', line.strip())  # NOSONAR
                        if match:
                            status_code = int(match.group(1))
                            request_time = float(match.group(2))

                            status_codes.append(status_code)
                            response_times.append(request_time)

            except Exception as e:
                logger.warning(f'分析日志文件 {log_path} 失败: {e}')
                continue

        if not response_times:
            return None

        # 计算百分位数
        response_times.sort()
        n = len(response_times)

        stats = {
            'tp99': f"{response_times[int(n * 0.99)] * 1000:.1f}",  # 转换为毫秒
            'tp95': f"{response_times[int(n * 0.95)] * 1000:.1f}",
            'tp90': f"{response_times[int(n * 0.90)] * 1000:.1f}",
            'avg_response_time': f"{(sum(response_times) / n) * 1000:.1f}",
            'min_response_time': f"{min(response_times) * 1000:.1f}",
            'max_response_time': f"{max(response_times) * 1000:.1f}"
        }

        # 统计状态码
        if status_codes:
            success_count = len([s for s in status_codes if 200 <= s < 300])
            redirect_count = len([s for s in status_codes if 300 <= s < 400])
            client_error_count = len([s for s in status_codes if 400 <= s < 500])
            server_error_count = len([s for s in status_codes if 500 <= s < 600])

            stats.update({
                'success_count': success_count,
                'redirect_count': redirect_count,
                'client_error_count': client_error_count,
                'server_error_count': server_error_count,
                'success_rate': f"{(success_count / len(status_codes)) * 100:.1f}"
            })

        return stats

    except Exception as e:
        logger.error(f'分析访问日志响应时间失败: {e}')
        return None
