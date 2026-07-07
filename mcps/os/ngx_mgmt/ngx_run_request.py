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

def fetch_request_statistics():
    """获取请求统计信息"""
    stats = {
        'total_requests': 'N/A',
        'qps': 'N/A',
        'requests_per_minute': 'N/A',
        'requests_per_hour': 'N/A',
        'handled_requests': 'N/A',
        'dropped_requests': 'N/A'
    }

    try:
        # 首先尝试通过stub_status获取
        stub_info = fetch_stub_status_info()
        if stub_info['enabled']:
            stub_stats = fetch_stub_status_stats(stub_info['location'])
            if stub_stats.get('total_requests'):
                stats['total_requests'] = stub_stats['total_requests']
                stats['handled_requests'] = stub_stats.get('handled_requests', 'N/A')

                # 计算QPS
                uptime = fetch_nginx_uptime()
                if uptime > 0 and stats['total_requests'] != 'N/A':
                    qps = stats['total_requests'] / uptime
                    stats['qps'] = f"{qps:.2f}"
                    stats['requests_per_minute'] = f"{qps * 60:.0f}"
                    stats['requests_per_hour'] = f"{qps * 3600:.0f}"

        # 尝试从访问日志获取更详细的统计
        log_stats = fetch_access_log_statistics()
        if log_stats:
            # 如果stub_status没有数据，使用日志数据
            if stats['total_requests'] == 'N/A' and log_stats.get('total_requests'):
                stats['total_requests'] = log_stats['total_requests']
                if log_stats.get('qps'):
                    stats['qps'] = log_stats['qps']

        # 计算丢弃的请求数
        if stats['handled_requests'] != 'N/A' and stats['total_requests'] != 'N/A':
            stats['dropped_requests'] = max(0, stats['total_requests'] - stats['handled_requests'])

        return stats

    except Exception as e:
        logger.error(f'获取请求统计失败: {e}')
        return stats

def fetch_stub_status_stats(status_url):
    """从stub_status页面获取统计信息"""
    stats = {}
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            body = response.text.strip()

            # 解析stub_status输出
            # server accepts handled requests
            # 16630948 16630948 31070465
            server_match = re.search(r'server\s+accepts\s+handled\s+requests\s*\n\s*(\d+)\s+(\d+)\s+(\d+)', body)  # NOSONAR
            if server_match:
                stats['total_requests'] = int(server_match.group(3))  # 第三个数字是总请求数
                stats['handled_requests'] = int(server_match.group(2))  # 第二个数字是处理的连接数

    except Exception as e:
        logger.error(f'获取stub_status统计失败: {e}')

    return stats

def fetch_response_time_statistics():
    """获取响应时间统计"""
    stats = {
        'tp99': 'N/A',
        'tp95': 'N/A',
        'tp90': 'N/A',
        'avg_response_time': 'N/A',
        'min_response_time': 'N/A',
        'max_response_time': 'N/A'
    }

    try:
        # 尝试从访问日志分析响应时间
        log_analysis = examine_access_log_response_time()
        if log_analysis:
            stats.update(log_analysis)

        # 尝试通过HTTP请求测试获取响应时间
        http_test_stats = fetch_http_response_time_test()
        if http_test_stats and stats['avg_response_time'] == 'N/A':
            stats.update(http_test_stats)

        return stats

    except Exception as e:
        logger.error(f'获取响应时间统计失败: {e}')
        return stats

def examine_access_log_response_time():
    """分析访问日志中的响应时间"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        response_times = []
        status_codes = []

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取最近1000行日志
                    lines = f.readlines()[-1000:]

                    for line in lines:
                        # 解析Nginx访问日志格式
                        # 常见格式: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" $request_time
                        match = re.search(r'"[^"]*"\s+(\d{3})\s+\d+\s+"[^"]*"\s+"[^"]*"(?:\s+"[^"]*")?\s+([\d.]+)$', line.strip())  # NOSONAR
                        if match:
                            status_code = int(match.group(1))
                            request_time = float(match.group(2))

                            status_codes.append(status_code)
                            response_times.append(request_time)

            except Exception as e:
                logger.warning(f'分析日志文件 {log_path} 失败: {e}')
                continue

        if not response_times:
            return None

        # 计算百分位数
        response_times.sort()
        n = len(response_times)

        stats = {
            'tp99': f"{response_times[int(n * 0.99)] * 1000:.1f}",  # 转换为毫秒
            'tp95': f"{response_times[int(n * 0.95)] * 1000:.1f}",
            'tp90': f"{response_times[int(n * 0.90)] * 1000:.1f}",
            'avg_response_time': f"{(sum(response_times) / n) * 1000:.1f}",
            'min_response_time': f"{min(response_times) * 1000:.1f}",
            'max_response_time': f"{max(response_times) * 1000:.1f}"
        }

        # 统计状态码
        if status_codes:
            success_count = len([s for s in status_codes if 200 <= s < 300])
            redirect_count = len([s for s in status_codes if 300 <= s < 400])
            client_error_count = len([s for s in status_codes if 400 <= s < 500])
            server_error_count = len([s for s in status_codes if 500 <= s < 600])

            stats.update({
                'success_count': success_count,
                'redirect_count': redirect_count,
                'client_error_count': client_error_count,
                'server_error_count': server_error_count,
                'success_rate': f"{(success_count / len(status_codes)) * 100:.1f}"
            })

        return stats

    except Exception as e:
        logger.error(f'分析访问日志响应时间失败: {e}')
        return None

def locate_access_log_paths():
    """查找访问日志文件路径"""
    log_paths = []
    try:
        # 从Nginx配置中查找访问日志路径
        output = subprocess.run(['nginx', '-T'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode in [0, 1]:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 查找access_log指令
            access_log_matches = re.findall(r'access_log\s+([^\s;]+)', output, re.IGNORECASE)  # NOSONAR
            for match in access_log_matches:
                if not match.endswith('off'):
                    log_paths.append(match)

        # 默认路径
        default_paths = [
            '/var/log/nginx/access.log',
            '/var/log/nginx/access.log.1',
            '/var/log/nginx/localhost.access.log',
            '/usr/local/nginx/logs/access.log',
            '/etc/nginx/logs/access.log'
        ]

        for path in default_paths:
            if path not in log_paths and os.path.exists(path):
                log_paths.append(path)

        return log_paths

    except Exception as e:
        logger.error(f'查找访问日志路径失败: {e}')
        return ['/var/log/nginx/access.log']

def fetch_http_response_time_test():
    """通过HTTP测试获取响应时间"""
    try:
        # 测试本地Nginx服务
        test_urls = [
            'http://localhost',  # NOSONAR
            'http://127.0.0.1',  # NOSONAR
            'http://localhost:80'  # NOSONAR
        ]

        response_times = []

        for url in test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # 转换为毫秒
                response_times.append(response_time)

                if len(response_times) >= 5:  # 最多测试5次
                    break

            except Exception as e:
                logger.warning(f'HTTP测试请求失败 {url}: {e}')
                continue

        if response_times:
            response_times.sort()
            n = len(response_times)

            return {
                'tp99': f"{response_times[int(n * 0.99)] if n > 1 else response_times[0]:.1f}",
                'tp95': f"{response_times[int(n * 0.95)] if n > 1 else response_times[0]:.1f}",
                'tp90': f"{response_times[int(n * 0.90)] if n > 1 else response_times[0]:.1f}",
                'avg_response_time': f"{sum(response_times) / n:.1f}",
                'min_response_time': f"{min(response_times):.1f}",
                'max_response_time': f"{max(response_times):.1f}"
            }

        return None

    except Exception as e:
        logger.error(f'HTTP响应时间测试失败: {e}')
        return None

def fetch_status_code_statistics():
    """获取状态码统计"""
    stats = {
        'success_count': 'N/A',
        'redirect_count': 'N/A',
        'client_error_count': 'N/A',
        'server_error_count': 'N/A',
        'success_rate': 'N/A'
    }

    try:
        # 从访问日志获取状态码统计
        log_stats = fetch_access_log_status_statistics()
        if log_stats:
            stats.update(log_stats)

        return stats

    except Exception as e:
        logger.error(f'获取状态码统计失败: {e}')
        return stats

def fetch_access_log_status_statistics():
    """从访问日志获取状态码统计"""
    try:
        # 查找访问日志文件
        access_log_paths = locate_access_log_paths()
        if not access_log_paths:
            return None

        status_codes = []

        for log_path in access_log_paths:
            if not os.path.exists(log_path):
                continue

            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # 读取最近1000行日志
                    lines = f.readlines()[-1000:]

                    for line in lines:
                        # 解析状态码
                        match = re.search(r'"[^"]*"\s+(\d{3})\s+', line.strip())  # NOSONAR
                        if match:
                            status_code = int(match.group(1))
                            status_codes.append(status_code)

            except Exception as e:
                logger.warning(f'分析日志文件 {log_path} 失败: {e}')
                continue

        if not status_codes:
            return None

        # 统计各类状态码
        success_count = len([s for s in status_codes if 200 <= s < 300])
        redirect_count = len([s for s in status_codes if 300 <= s < 400])
        client_error_count = len([s for s in status_codes if 400 <= s < 500])
        server_error_count = len([s for s in status_codes if 500 <= s < 600])
        total_count = len(status_codes)

        return {
            'success_count': success_count,
            'redirect_count': redirect_count,
            'client_error_count': client_error_count,
            'server_error_count': server_error_count,
            'success_rate': f"{(success_count / total_count) * 100:.1f}" if total_count > 0 else "0.0"
        }

    except Exception as e:
        logger.error(f'分析访问日志状态码失败: {e}')
        return None

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

def fetch_nginx_uptime():
    """获取Nginx运行时间（秒）"""
    try:
        # 获取master进程的启动时间
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.cmdline()) if hasattr(proc, 'cmdline') else ''
                    if 'master' in cmdline.lower():
                        create_time = proc.info.get('create_time')
                        if create_time:
                            return int(time.time() - create_time)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return 0
    except Exception as e:
        logger.error(f'获取Nginx运行时间失败: {e}')
        return 0

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_runtime_request",
    "function": fetch_nginx_runtime_request,
    "description": "获取Nginx运行时请求统计，包括总请求数、QPS、TP99/TP95响应时间、成功/失败请求数等",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

# 如果直接运行此脚本
if __name__ == "__main__":
    print(fetch_nginx_runtime_request())
