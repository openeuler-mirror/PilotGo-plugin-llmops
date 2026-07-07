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


def fetch_access_log_statistics():
    """从访问日志获取统计信息"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        total_requests = 0
        time_range = None

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total_requests += len(lines)

                    if lines and not time_range:
                        # 尝试解析时间范围
                        first_line = lines[0]
                        last_line = lines[-1]

                        # 简单的日志时间解析
                        time_match1 = re.search(r'\[([^\]]+)\]', first_line)  # NOSONAR
                        time_match2 = re.search(r'\[([^\]]+)\]', last_line)  # NOSONAR

                        if time_match1 and time_match2:
                            time_range = {
                                'start': time_match1.group(1),
                                'end': time_match2.group(1)
                            }

            except Exception as e:
                logger.warning(f'分析日志文件 {log_path} 失败: {e}')
                continue

        if total_requests == 0:
            return None

        # 估算QPS
        qps = 'N/A'
        if time_range:
            # 简化的QPS计算
            qps = f"{total_requests / 3600:.2f}"  # 假设日志覆盖1小时

        return {
            'total_requests': total_requests,
            'qps': qps,
            'time_range': time_range
        }

    except Exception as e:
        logger.error(f'分析访问日志统计失败: {e}')
        return None
