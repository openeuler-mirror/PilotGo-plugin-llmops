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


def fetch_optimization_suggestions(request_stats, response_time_stats, status_stats):
    """获取性能优化建议"""
    suggestions = []

    try:
        # 响应时间优化建议
        if response_time_stats and response_time_stats.get('avg_response_time') != 'N/A':
            avg_time = float(response_time_stats['avg_response_time'])
            if avg_time > 1000:
                suggestions.append("响应时间超过1秒，建议优化后端服务性能")
                suggestions.append("考虑启用Nginx缓存减少后端压力")
            elif avg_time > 500:
                suggestions.append("响应时间较长，建议检查数据库查询和API性能")

        # TP99优化建议
        if response_time_stats and response_time_stats.get('tp99') != 'N/A':
            tp99 = float(response_time_stats['tp99'])
            if tp99 > 3000:
                suggestions.append("TP99响应时间过长，存在长尾请求问题")
                suggestions.append("建议分析慢查询和复杂请求的处理逻辑")

        # 错误率优化建议
        if status_stats and status_stats.get('success_rate') != 'N/A':
            success_rate = float(status_stats['success_rate'])
            if success_rate < 95:
                suggestions.append("成功率低于95%，需要排查错误原因")
                if status_stats.get('server_error_count') != 'N/A' and status_stats['server_error_count'] > 0:
                    suggestions.append("存在服务器错误，建议检查后端服务状态")
                if status_stats.get('client_error_count') != 'N/A' and status_stats['client_error_count'] > 0:
                    suggestions.append("存在客户端错误，建议检查请求参数和URL配置")

        # QPS优化建议
        if request_stats.get('qps') != 'N/A':
            qps = float(request_stats['qps'])
            if qps > 100:
                suggestions.append("QPS较高，建议启用Nginx缓存和负载均衡")
                suggestions.append("考虑使用CDN分担静态资源请求压力")

        if not suggestions:
            suggestions.append("当前性能表现良好，暂无优化建议")

        return suggestions

    except Exception as e:
        logger.error(f'获取优化建议失败: {e}')
        return ["获取优化建议失败"]
