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


def examine_request_performance(request_stats, response_time_stats, status_stats):
    """分析请求性能"""
    analysis = []

    try:
        # QPS分析
        if request_stats.get('qps') != 'N/A':
            qps = float(request_stats['qps'])
            if qps < 1:
                analysis.append("📉 低QPS - 网站流量较少")
            elif qps < 10:
                analysis.append("📊 中等QPS - 正常流量水平")
            elif qps < 100:
                analysis.append("📈 较高QPS - 活跃的网站")
            else:
                analysis.append("🚀 高QPS - 高流量网站")

        # 响应时间分析
        if response_time_stats and response_time_stats.get('avg_response_time') != 'N/A':
            avg_time = float(response_time_stats['avg_response_time'])
            if avg_time < 100:
                analysis.append("⚡ 响应时间优秀 - 平均响应时间小于100ms")
            elif avg_time < 500:
                analysis.append("✅ 响应时间良好 - 平均响应时间小于500ms")
            elif avg_time < 1000:
                analysis.append("⚠️  响应时间一般 - 平均响应时间小于1s")
            else:
                analysis.append("🐌 响应时间较慢 - 建议优化性能")

        # TP99分析
        if response_time_stats and response_time_stats.get('tp99') != 'N/A':
            tp99 = float(response_time_stats['tp99'])
            if tp99 < 1000:
                analysis.append("🎯 TP99表现优秀 - 99%请求响应时间小于1s")
            elif tp99 < 3000:
                analysis.append("📊 TP95表现良好 - 99%请求响应时间小于3s")
            else:
                analysis.append("⚠️  TP99需要优化 - 存在长尾延迟问题")

        # 成功率分析
        if status_stats and status_stats.get('success_rate') != 'N/A':
            success_rate = float(status_stats['success_rate'])
            if success_rate >= 99:
                analysis.append("✅ 成功率优秀 - 错误率极低")
            elif success_rate >= 95:
                analysis.append("📊 成功率良好 - 正常水平")
            elif success_rate >= 90:
                analysis.append("⚠️  成功率一般 - 存在一定错误")
            else:
                analysis.append("🚨 成功率较低 - 需要排查错误原因")

        # 错误分析
        if status_stats and status_stats.get('server_error_count') != 'N/A':
            server_errors = status_stats['server_error_count']
            if isinstance(server_errors, int) and server_errors > 0:
                analysis.append(f"🐛 存在服务器错误 - 5xx错误数: {server_errors}")

        if not analysis:
            analysis.append("ℹ️  暂无性能分析数据")

        return analysis

    except Exception as e:
        logger.error(f'分析请求性能失败: {e}')
        return ["❌ 性能分析失败"]
