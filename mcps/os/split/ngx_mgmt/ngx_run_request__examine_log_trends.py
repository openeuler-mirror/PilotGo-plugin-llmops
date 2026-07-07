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


def examine_log_trends():
    """分析日志趋势"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        # 简化的趋势分析 - 基于最近1小时的数据
        trends = []

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-500:]  # 最近500条记录

                    if len(lines) < 10:
                        continue

                    # 简单的时间分布分析
                    time_distribution = {}

                    for line in lines:
                        # 提取时间戳
                        time_match = re.search(r'\[([^\]]+)\]', line)  # NOSONAR
                        if time_match:
                            time_str = time_match.group(1)
                            # 简化时间解析，只取小时
                            hour_match = re.search(r':(\d{2}):', time_str)  # NOSONAR
                            if hour_match:
                                hour = hour_match.group(1)
                                time_distribution[hour] = time_distribution.get(hour, 0) + 1

                    if time_distribution:
                        current_hour = datetime.now().strftime('%H')
                        current_count = time_distribution.get(current_hour, 0)

                        # 与平均值比较
                        avg_count = sum(time_distribution.values()) / len(time_distribution)

                        if current_count > avg_count * 1.5:
                            trends.append("🚀 当前小时请求量高于平均水平50%以上")
                        elif current_count < avg_count * 0.5:
                            trends.append("📉 当前小时请求量低于平均水平50%以上")
                        else:
                            trends.append("📊 当前小时请求量处于正常范围")

                        break  # 只分析第一个有效的日志文件

            except Exception as e:
                logger.warning(f'分析日志趋势失败 {log_path}: {e}')
                continue

        return trends if trends else None

    except Exception as e:
        logger.error(f'分析日志趋势失败: {e}')
        return None
