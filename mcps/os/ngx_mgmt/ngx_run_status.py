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

def fetch_connection_status():
    """获取连接状态"""
    try:
        # 尝试从Nginx状态模块获取连接信息
        status_url = fetch_status_module_url()
        if status_url:
            try:
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    payload = response.read().decode('utf-8')
                    # 解析Nginx状态页面
                    active = re.search(r'Active connections: (\d+)', payload)  # NOSONAR
                    accepts = re.search(r'(\d+)\s+accepts', payload)  # NOSONAR
                    handled = re.search(r'(\d+)\s+handled', payload)  # NOSONAR
                    requests = re.search(r'(\d+)\s+requests', payload)  # NOSONAR
                    reading = re.search(r'Reading: (\d+)', payload)  # NOSONAR
                    writing = re.search(r'Writing: (\d+)', payload)  # NOSONAR
                    waiting = re.search(r'Waiting: (\d+)', payload)  # NOSONAR

                    return {
                        'active': int(active.group(1)) if active else 0,
                        'accepts': int(accepts.group(1)) if accepts else 0,
                        'handled': int(handled.group(1)) if handled else 0,
                        'requests': int(requests.group(1)) if requests else 0,
                        'reading': int(reading.group(1)) if reading else 0,
                        'writing': int(writing.group(1)) if writing else 0,
                        'waiting': int(waiting.group(1)) if waiting else 0
                    }
            except Exception as e:
                logger.warning(f'从状态模块获取连接信息失败: {e}')

        # 如果无法从状态模块获取，尝试从系统获取
        proc_info = get_nginx_process_info()
        nginx_pids = proc_info.get('pids', [])
        active = 0

        for pid in nginx_pids:
            try:
                proc = psutil.Process(pid)
                connections = proc.connections()
                active += len([c for c in connections if c.state == 'ESTABLISHED'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'active': active,
            'accepts': 0,
            'handled': 0,
            'requests': 0,
            'reading': 0,
            'writing': 0,
            'waiting': 0
        }
    except Exception as e:
        logger.error(f'获取连接状态失败: {e}')
        return {
            'active': 0,
            'accepts': 0,
            'handled': 0,
            'requests': 0,
            'reading': 0,
            'writing': 0,
            'waiting': 0
        }

def fetch_request_stats():
    """获取请求统计"""
    try:
        # 尝试从Nginx状态模块获取请求信息
        status_url = fetch_status_module_url()
        if status_url:
            try:
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    payload = response.read().decode('utf-8')
                    # 解析请求统计
                    requests = re.search(r'(\d+)\s+requests', payload)  # NOSONAR
                    if requests:
                        # 简单计算每秒请求数（基于总请求数和运行时间）
                        proc_info = get_nginx_process_info()
                        nginx_pids = proc_info.get('pids', [])

                        uptime_seconds = 0
                        for pid in nginx_pids:
                            try:
                                proc = psutil.Process(pid)
                                cmdline = ' '.join(proc.cmdline()).lower()
                                if 'master' in cmdline:
                                    create_time = proc.create_time()
                                    uptime_seconds = time.time() - create_time
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue

                        if uptime_seconds > 0:
                            req_per_sec = int(requests.group(1)) / uptime_seconds
                            return {
                                'total': int(requests.group(1)),
                                'req_per_sec': f"{req_per_sec:.1f}"
                            }
            except Exception as e:
                logger.warning(f'从状态模块获取请求统计失败: {e}')

        # 如果无法从状态模块获取，返回默认值
        return {
            'total': 0,
            'req_per_sec': "未知"
        }
    except Exception as e:
        logger.error(f'获取请求统计失败: {e}')
        return {
            'total': 0,
            'req_per_sec': "未知"
        }

def fetch_cache_status():
    """获取缓存状态"""
    try:
        # 尝试从Nginx状态模块获取缓存信息
        status_url = fetch_status_module_url()
        if status_url:
            try:
                with urllib.request.urlopen(status_url, timeout=5) as response:
                    payload = response.read().decode('utf-8')
                    # 解析缓存统计
                    cache_hits = re.search(r'(\d+)\s+cache hits', payload)  # NOSONAR
                    cache_misses = re.search(r'(\d+)\s+cache misses', payload)  # NOSONAR

                    if cache_hits and cache_misses:
                        hits = int(cache_hits.group(1))
                        misses = int(cache_misses.group(1))
                        total = hits + misses
                        hit_rate = f"{(hits / total) * 100:.1f}%" if total > 0 else "0%"
                        return {
                            'hits': hits,
                            'misses': misses,
                            'hit_rate': hit_rate
                        }
            except Exception as e:
                logger.warning(f'从状态模块获取缓存状态失败: {e}')

        # 如果无法从状态模块获取，返回默认值
        return {
            'hits': 0,
            'misses': 0,
            'hit_rate': "未知"
        }
    except Exception as e:
        logger.error(f'获取缓存状态失败: {e}')
        return {
            'hits': 0,
            'misses': 0,
            'hit_rate': "未知"
        }

def fetch_resource_usage(pids):
    """获取资源使用情况"""
    try:
        total_cpu = 0
        total_memory = 0

        for pid in pids:
            try:
                proc = psutil.Process(pid)
                cpu_percent = proc.cpu_percent(interval=0.1)
                memory_percent = proc.memory_percent()

                total_cpu += cpu_percent
                total_memory += memory_percent
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            'cpu': f"{total_cpu:.1f}",
            'memory': f"{total_memory:.1f}"
        }
    except Exception as e:
        logger.error(f'获取资源使用情况失败: {e}')
        return {
            'cpu': "未知",
            'memory': "未知"
        }

def fetch_status_module_url():
    """获取Nginx状态模块URL"""
    try:
        # 尝试从配置文件中获取状态模块配置
        cfg_filepath = get_nginx_config_path()
        if not cfg_filepath:
            return None

        with open(cfg_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 查找stub_status配置
        status_location = re.search(r'location\s+([^\s]+)\s*{[^}]*stub_status[^}]*}', body, re.DOTALL)  # NOSONAR
        if status_location:
            location = status_location.group(1).strip()
            # 查找监听端口
            listen_match = re.search(r'listen\s+([^;]+);', body)  # NOSONAR
            if listen_match:
                listen = listen_match.group(1).strip()
                # 处理默认端口
                if listen == 'default_server' or listen == 'default':
                    listen = '80'

                # 构建URL
                if ':' in listen:
                    host, port = listen.split(':')
                else:
                    port = listen
                    host = '127.0.0.1'

                return f"http://{host}:{port}{location}"  # NOSONAR

        # 如果找不到配置，尝试默认位置
        return "http://127.0.0.1/nginx_status"  # NOSONAR
    except Exception as e:
        logger.warning(f'获取状态模块URL失败: {e}')
        return None