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


def fetch_request_trend_analysis():
    """获取请求趋势分析"""
    trends = []

    try:
        # 从日志文件分析趋势
        log_trends = examine_log_trends()
        if log_trends:
            trends.extend(log_trends)

        # 基于当前数据简单分析
        request_stats = fetch_request_statistics()
        if request_stats.get('qps') != 'N/A':
            qps = float(request_stats['qps'])
            if qps > 50:
                trends.append("📈 当前QPS较高，可能处于流量高峰期")
            elif qps < 1:
                trends.append("📉 当前QPS较低，可能处于流量低谷期")
            else:
                trends.append("📊 当前QPS处于正常水平")

        if not trends:
            trends.append("ℹ️  暂无趋势分析数据")

        return trends

    except Exception as e:
        logger.error(f'获取请求趋势分析失败: {e}')
        return ["❌ 趋势分析失败"]
