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

def fetch_stub_status_info():
    """获取stub_status模块信息"""
    try:
        # 检查nginx配置中是否启用了stub_status
        output = subprocess.run(['nginx', '-T'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode in [0, 1]:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 查找stub_status配置
            stub_status_matches = re.findall(r'location\s+([^/]*)/nginx_status\s*{[^}]*stub_status', output, re.IGNORECASE | re.DOTALL)  # NOSONAR
            if not stub_status_matches:
                stub_status_matches = re.findall(r'location\s+([^/]*)/status\s*{[^}]*stub_status', output, re.IGNORECASE | re.DOTALL)  # NOSONAR

            if stub_status_matches:
                location = stub_status_matches[0].strip() if stub_status_matches[0].strip() else ''
                return {
                    'enabled': True,
                    'location': f"{location}/nginx_status" if location else "/nginx_status",
                    'message': 'stub_status模块已配置'
                }

        # 尝试常见的状态页面URL
        common_urls = [
            'http://localhost/nginx_status',  # NOSONAR
            'http://127.0.0.1/nginx_status',  # NOSONAR
            'http://localhost/status',  # NOSONAR
            'http://127.0.0.1/status'  # NOSONAR
        ]

        for url in common_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200 and 'Active connections' in response.text:
                    return {
                        'enabled': True,
                        'location': url,
                        'message': f'stub_status模块可通过 {url} 访问'
                    }
            except Exception:
                continue

        return {'enabled': False, 'message': 'stub_status模块未启用或无法访问'}

    except Exception as e:
        logger.error(f'获取stub_status信息失败: {e}')
        return {'enabled': False, 'message': f'检测失败: {e}'}

def fetch_connection_statistics():
    """获取连接统计信息"""
    stats = {
        'active_connections': 'N/A',
        'reading_connections': 'N/A',
        'writing_connections': 'N/A',
        'waiting_connections': 'N/A',
        'total_connections': 'N/A',
        'total_handshakes': 'N/A',
        'total_requests': 'N/A',
        'connections_per_second': 'N/A',
        'requests_per_second': 'N/A'
    }

    try:
        # 首先尝试通过stub_status获取
        stub_info = fetch_stub_status_info()
        if stub_info['enabled']:
            stats.update(fetch_stub_status_stats(stub_info['location']))

        # 补充系统级连接信息
        system_stats = fetch_system_connection_stats()
        if stats['active_connections'] == 'N/A' and system_stats['tcp_established'] != 'N/A':
            # 估算活跃连接数（Nginx进程相关的ESTABLISHED连接）
            nginx_connections = fetch_nginx_estimated_connections()
            if nginx_connections > 0:
                stats['active_connections'] = nginx_connections

        # 计算连接率（如果可能）
        if stats['total_connections'] != 'N/A' and stats['total_connections'] > 0:
            # 获取Nginx运行时间
            uptime = fetch_nginx_uptime()
            if uptime > 0:
                stats['connections_per_second'] = round(stats['total_connections'] / uptime, 2)

        return stats

    except Exception as e:
        logger.error(f'获取连接统计失败: {e}')
        return stats

def fetch_stub_status_stats(status_url):
    """从stub_status页面获取统计信息"""
    stats = {}
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            body = response.text.strip()

            # 解析stub_status输出
            # Active connections: 291
            active_match = re.search(r'Active connections:\s*(\d+)', body)  # NOSONAR
            if active_match:
                stats['active_connections'] = int(active_match.group(1))

            # server accepts handled requests
            # 16630948 16630948 31070465
            server_match = re.search(r'server\s+accepts\s+handled\s+requests\s*\n\s*(\d+)\s+(\d+)\s+(\d+)', body)  # NOSONAR
            if server_match:
                stats['total_connections'] = int(server_match.group(1))
                stats['total_handshakes'] = int(server_match.group(2))
                stats['total_requests'] = int(server_match.group(3))

            # Reading: 6 Writing: 179 Waiting: 106
            reading_match = re.search(r'Reading:\s*(\d+)', body)  # NOSONAR
            writing_match = re.search(r'Writing:\s*(\d+)', body)  # NOSONAR
            waiting_match = re.search(r'Waiting:\s*(\d+)', body)  # NOSONAR

            if reading_match:
                stats['reading_connections'] = int(reading_match.group(1))
            if writing_match:
                stats['writing_connections'] = int(writing_match.group(1))
            if waiting_match:
                stats['waiting_connections'] = int(waiting_match.group(1))

    except Exception as e:
        logger.error(f'获取stub_status统计失败: {e}')

    return stats

def fetch_nginx_estimated_connections():
    """估算Nginx的ESTABLISHED连接数"""
    try:
        nginx_connections = 0
        # 获取所有Nginx进程的连接
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                if proc.details['name'] and 'nginx' in proc.details['name'].lower():
                    connections = proc.details.get('connections', [])
                    if connections:
                        established = [conn for conn in connections if conn.status == 'ESTABLISHED']
                        nginx_connections += len(established)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return nginx_connections
    except Exception as e:
        logger.error(f'估算Nginx连接数失败: {e}')
        return 0

def fetch_nginx_uptime():
    """获取Nginx运行时间（秒）"""
    try:
        # 获取master进程的启动时间
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.details['name'] and 'nginx' in proc.details['name'].lower():
                    cmdline = ' '.join(proc.cmdline()) if hasattr(proc, 'cmdline') else ''
                    if 'master' in cmdline.lower():
                        create_time = proc.details.get('create_time')
                        if create_time:
                            return int(time.time() - create_time)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return 0
    except Exception as e:
        logger.error(f'获取Nginx运行时间失败: {e}')
        return 0

def examine_connection_thresholds(connection_stats):
    """分析连接数阈值"""
    analysis = {
        'max_connections_threshold': 'N/A',
        'usage_percentage': 'N/A',
        'threshold_status': 'N/A',
        'worker_processes': 'N/A',
        'worker_connections': 'N/A'
    }

    try:
        # 获取Nginx配置信息
        worker_info = fetch_nginx_worker_info()
        analysis.update(worker_info)

        if worker_info['worker_processes'] != 'N/A' and worker_info['worker_connections'] != 'N/A':
            # 计算最大连接数阈值
            # 理论最大值 = worker_processes * worker_connections
            max_connections = worker_info['worker_processes'] * worker_info['worker_connections']
            analysis['max_connections_threshold'] = max_connections

            # 计算当前使用率
            active_connections = connection_stats.get('active_connections', 0)
            if active_connections != 'N/A' and active_connections > 0:
                usage_percentage = (active_connections / max_connections) * 100
                analysis['usage_percentage'] = f"{usage_percentage:.1f}%"

                # 阈值状态判断
                if usage_percentage >= 90:
                    analysis['threshold_status'] = "🔴 危险 - 接近最大容量"
                elif usage_percentage >= 80:
                    analysis['threshold_status'] = "🟡 警告 - 高负载状态"
                elif usage_percentage >= 60:
                    analysis['threshold_status'] = "🟢 正常 - 中等负载"
                else:
                    analysis['threshold_status'] = "🟢 良好 - 低负载状态"
            else:
                analysis['threshold_status'] = "⚪ 未知 - 无法计算使用率"

        return analysis

    except Exception as e:
        logger.error(f'分析连接阈值失败: {e}')
        return analysis