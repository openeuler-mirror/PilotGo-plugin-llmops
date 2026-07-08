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

def fetch_nginx_runtime_request():
    """
    获取Nginx运行时请求统计的MCP工具，包括：
    - 总请求数 (Total requests)
    - QPS (Queries Per Second)
    - TP99/TP95响应时间
    - 成功/失败请求数
    - 请求状态码分布
    - 请求性能分析
    """
    try:
        output = []
        output.append('=== Nginx运行时请求统计监控 ===')

        # 检查Nginx是否运行
        nginx_status = verify_nginx_running()
        if not nginx_status['running']:
            output.append(f"Nginx状态: {nginx_status['message']}")
            return '\n'.join(output)

        output.append("Nginx状态: 运行中")

        # 获取stub_status模块信息
        stub_status_info = fetch_stub_status_info()
        output.append(f"stub_status模块: {'已启用' if stub_status_info['enabled'] else '未启用'}")

        # 获取请求统计信息
        request_stats = fetch_request_statistics()
        output.append('\n=== 请求统计信息 ===')

        # 总请求数
        output.append(f"总请求数: {request_stats.get('total_requests', 'N/A'):,}")

        # QPS计算
        if request_stats.get('qps') != 'N/A':
            output.append(f"QPS (每秒查询数): {request_stats['qps']}")

        # 响应时间分析
        response_time_stats = fetch_response_time_statistics()
        if response_time_stats:
            output.append('\n=== 响应时间统计 ===')
            if response_time_stats.get('tp99') != 'N/A':
                output.append(f"TP99响应时间: {response_time_stats['tp99']}ms")
            if response_time_stats.get('tp95') != 'N/A':
                output.append(f"TP95响应时间: {response_time_stats['tp95']}ms")
            if response_time_stats.get('avg_response_time') != 'N/A':
                output.append(f"平均响应时间: {response_time_stats['avg_response_time']}ms")

        # 成功/失败请求数
        status_stats = fetch_status_code_statistics()
        if status_stats:
            output.append('\n=== 请求状态统计 ===')
            output.append(f"成功请求数 (2xx): {status_stats.get('success_count', 'N/A'):,}")
            output.append(f"重定向请求数 (3xx): {status_stats.get('redirect_count', 'N/A'):,}")
            output.append(f"客户端错误数 (4xx): {status_stats.get('client_error_count', 'N/A'):,}")
            output.append(f"服务器错误数 (5xx): {status_stats.get('server_error_count', 'N/A'):,}")
            if status_stats.get('success_rate') != 'N/A':
                output.append(f"成功率: {status_stats['success_rate']}%")

        # 请求性能分析
        performance_analysis = examine_request_performance(request_stats, response_time_stats, status_stats)
        if performance_analysis:
            output.append('\n=== 请求性能分析 ===')
            for analysis in performance_analysis:
                output.append(f"  {analysis}")

        # 请求趋势分析
        trend_analysis = fetch_request_trend_analysis()
        if trend_analysis:
            output.append('\n=== 请求趋势分析 ===')
            for trend in trend_analysis:
                output.append(f"  {trend}")

        # 性能优化建议
        optimization_suggestions = fetch_optimization_suggestions(request_stats, response_time_stats, status_stats)
        if optimization_suggestions:
            output.append('\n=== 性能优化建议 ===')
            for suggestion in optimization_suggestions:
                output.append(f"  • {suggestion}")

        output.append('\n==========================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx请求统计失败: {e}')
        return f'获取Nginx请求统计失败: {e}'

def verify_nginx_running():
    """检查Nginx是否正在运行"""
    try:
        output = subprocess.run(['pgrep', '-f', 'nginx'], capture_output=True, text=True)
        if output.returncode == 0:
            pids = output.stdout.strip().split('\n')
            master_pids = []
            for pid in pids:
                try:
                    proc = psutil.Process(int(pid))
                    if 'master' in ' '.join(proc.cmdline()).lower():
                        master_pids.append(pid)
                except Exception:
                    continue

            return {'running': True, 'message': 'Nginx主进程正在运行', 'master_pids': master_pids} if master_pids else {'running': True, 'message': 'Nginx工作进程正在运行', 'worker_pids': pids}
        else:
            return {'running': False, 'message': 'Nginx服务未运行'}
    except Exception as e:
        logger.error(f'检查Nginx运行状态失败: {e}')
        return {'running': False, 'message': f'检查失败: {e}'}