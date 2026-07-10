from typing import Dict, Optional
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
logger = logging.getLogger('nginx_runtime_connect')

def fetch_nginx_runtime_connect():
    """
    获取Nginx运行时连接状态的MCP工具，包括：
    - 活跃连接数 (Active connections)
    - 总连接数 (Total connections)
    - 等待连接数 (Waiting connections)
    - 读取连接数 (Reading connections)
    - 写入连接数 (Writing connections)
    - 最大连接数阈值监控
    - 连接状态分析和告警
    """
    try:
        output = []
        output.append('=== Nginx运行时连接状态监控 ===')

        # 检查Nginx是否运行
        nginx_status = verify_nginx_running()
        if not nginx_status['running']:
            output.append(f"Nginx状态: {nginx_status['message']}")
            return '\n'.join(output)

        output.append("Nginx状态: 运行中")

        # 获取stub_status模块信息
        stub_status_info = fetch_stub_status_info()
        output.append(f"stub_status模块: {'已启用' if stub_status_info['enabled'] else '未启用'}")

        # 获取连接统计信息
        connection_stats = fetch_connection_statistics()
        output.append('\n=== 连接统计信息 ===')

        # 活跃连接数
        output.append(f"活跃连接数: {connection_stats.get('active_connections', 'N/A')}")

        # 读取/写入/等待连接数
        output.append(f"读取连接数: {connection_stats.get('reading_connections', 'N/A')}")
        output.append(f"写入连接数: {connection_stats.get('writing_connections', 'N/A')}")
        output.append(f"等待连接数: {connection_stats.get('waiting_connections', 'N/A')}")

        # 总连接统计
        output.append('\n=== 总连接统计 ===')
        output.append(f"总连接数: {connection_stats.get('total_connections', 'N/A')}")
        output.append(f"总握手数: {connection_stats.get('total_handshakes', 'N/A')}")
        output.append(f"总请求数: {connection_stats.get('total_requests', 'N/A')}")

        # 连接率统计
        if 'connections_per_second' in connection_stats:
            output.append(f"连接率: {connection_stats['connections_per_second']}/秒")
        if 'requests_per_second' in connection_stats:
            output.append(f"请求率: {connection_stats['requests_per_second']}/秒")

        # 最大连接数阈值分析
        threshold_analysis = examine_connection_thresholds(connection_stats)
        output.append('\n=== 连接阈值分析 ===')
        output.append(f"最大连接数阈值: {threshold_analysis.get('max_connections_threshold', 'N/A')}")
        output.append(f"当前使用率: {threshold_analysis.get('usage_percentage', 'N/A')}")
        output.append(f"阈值状态: {threshold_analysis.get('threshold_status', 'N/A')}")

        # 连接状态检查
        connection_checks = verify_connection_health(connection_stats, threshold_analysis)
        if connection_checks:
            output.append('\n=== 连接健康检查 ===')
            for check in connection_checks:
                output.append(f"  {check}")

        # 系统级连接统计
        system_connections = fetch_system_connection_stats()
        output.append('\n=== 系统级连接统计 ===')
        output.append(f"系统TCP连接数: {system_connections.get('tcp_total', 'N/A')}")
        output.append(f"系统ESTABLISHED连接: {system_connections.get('tcp_established', 'N/A')}")
        output.append(f"系统TIME_WAIT连接: {system_connections.get('tcp_time_wait', 'N/A')}")

        # 性能建议
        performance_suggestions = fetch_performance_suggestions(connection_stats, threshold_analysis)
        if performance_suggestions:
            output.append('\n=== 性能优化建议 ===')
            for suggestion in performance_suggestions:
                output.append(f"  • {suggestion}")

        output.append('\n==========================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx连接状态失败: {e}')
        return f'获取Nginx连接状态失败: {e}'

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