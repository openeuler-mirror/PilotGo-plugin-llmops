from datetime import datetime
import logging
import os
import re
import time
import urllib.request
import urllib.request
import urllib.request

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_status')

def fetch_nginx_runtime_status():
    """
    聚合获取Nginx运行时核心指标，包括：
    - 进程状态
    - 连接状态
    - 请求统计
    - 缓存状态
    输出极简健康快照
    """
    try:
        output = []
        output.append('=== Nginx运行时健康快照 ===')

        # 获取nginx进程信息
        proc_info = get_nginx_process_info()
        if proc_info['state'] == '已停止':
            output.append('状态: 🔴 离线')
            output.append('Nginx服务未运行')
            return '\n'.join(output)

        # 获取nginx进程PID列表
        nginx_pids = proc_info.get('pids', [])
        if not nginx_pids:
            output.append('状态: 🔴 异常')
            output.append('未找到Nginx进程')
            return '\n'.join(output)

        # 获取进程状态
        process_status = fetch_process_status(nginx_pids)

        # 获取连接状态
        connection_status = fetch_connection_status()

        # 获取请求统计
        request_stats = fetch_request_stats()

        # 获取缓存状态
        cache_status = fetch_cache_status()

        # 获取系统资源使用
        resource_usage = fetch_resource_usage(nginx_pids)

        # 综合健康状态评估
        health_score = compute_health_score(process_status, connection_status,
                                            request_stats, cache_status, resource_usage)

        # 输出极简健康快照
        output.append(f"状态: {health_score['state']} {health_score['icon']}")
        output.append(f"健康评分: {health_score['score']}/100")
        output.append(f"运行时间: {process_status['uptime']}")
        output.append(f"进程数: {process_status['count']} (主: {process_status['master']}, 工: {process_status['workers']})")
        output.append(f"活跃连接: {connection_status['active']}")
        output.append(f"请求/秒: {request_stats['req_per_sec']}")
        output.append(f"缓存命中率: {cache_status['hit_rate']}")
        output.append(f"资源使用: CPU {resource_usage['cpu']}%, 内存 {resource_usage['memory']}%")

        # 警告信息
        if health_score['warnings']:
            output.append("\n⚠️ 警告:")
            for warning in health_score['warnings']:
                output.append(f"  - {warning}")

        output.append('\n========================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx运行时状态失败: {e}')
        return f'获取Nginx运行时状态失败: {e}'

def fetch_process_status(pids):
    """获取进程状态"""
    try:
        master_count = 0
        worker_count = 0
        total_count = 0
        uptime = "未知"

        for pid in pids:
            try:
                proc = psutil.Process(pid)
                cmdline = ' '.join(proc.cmdline()).lower()

                if 'master' in cmdline:
                    master_count += 1
                    # 获取主进程启动时间
                    create_time = proc.create_time()
                    start_time = datetime.fromtimestamp(create_time)
                    uptime_delta = datetime.now() - start_time
                    uptime = f"{uptime_delta.days}天 {uptime_delta.seconds//3600}小时 {(uptime_delta.seconds%3600)//60}分钟"
                elif 'worker' in cmdline:
                    worker_count += 1

                total_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'count': total_count,
            'master': master_count,
            'workers': worker_count,
            'uptime': uptime
        }
    except Exception as e:
        logger.error(f'获取进程状态失败: {e}')
        return {
            'count': 0,
            'master': 0,
            'workers': 0,
            'uptime': "未知"
        }