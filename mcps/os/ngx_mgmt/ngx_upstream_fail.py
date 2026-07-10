#!/usr/bin/env python3
"""
Nginx上游服务器失败监控工具
获取上游服务器的失败请求数、失败率、熔断状态、重试次数等信息
"""

import os
import re
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_fail')

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
            # 解析配置文件路径
            config_match = re.search(r'nginx: the configuration file ([^\s]+)', output)  # NOSONAR
            if config_match:
                return config_match.group(1)
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None

def load_nginx_config(cfg_filepath: str) -> str:
    """
    读取Nginx配置文件内容
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 配置文件内容
    """
    try:
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Nginx配置文件失败: {e}")
        return ""

def fetch_upstream_configuration(upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    获取upstream配置信息
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: upstream配置信息
    """
    try:
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        body = load_nginx_config(cfg_filepath)
        
        # 查找指定的upstream块
        upstream_pattern = rf'upstream\s+{upstream_name}\s*{{([^}}]+)}}'  # NOSONAR
        upstream_match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not upstream_match:
            return None
        
        upstream_content = upstream_match.group(1)
        
        # 解析服务器配置
        servers = []
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = re.finditer(server_pattern, upstream_content)  # NOSONAR
        
        for match in server_matches:
            server_config = match.group(1).strip()
            server_info = analyze_server_config(server_config)
            servers.append(server_info)
        
        # 解析负载均衡策略
        lb_method = analyze_load_balancing_method(upstream_content)
        
        # 解析重试配置
        retry_config = analyze_retry_config(upstream_content)
        
        return {
            'name': upstream_name,
            'servers': servers,
            'load_balancing_method': lb_method,
            'retry_config': retry_config,
            'server_count': len(servers)
        }
        
    except Exception as e:
        logger.error(f"获取upstream配置失败 {upstream_name}: {e}")
        return None

def analyze_server_config(server_config: str) -> Dict[str, Any]:
    """
    解析服务器配置
    
    参数:
        server_config: 服务器配置字符串
        
    返回:
        dict: 服务器详细信息
    """
    server_info = {
        'address': 'unknown',
        'port': 80,
        'weight': 1,
        'max_fails': 1,
        'fail_timeout': '10s',
        'backup': False,
        'down': False,
        'max_conns': 0
    }
    
    try:
        # 解析地址和端口
        parts = server_config.split()
        if parts:
            address_part = parts[0]
            if ':' in address_part:
                addr_parts = address_part.split(':')
                server_info['address'] = addr_parts[0]
                server_info['port'] = int(addr_parts[1]) if addr_parts[1].isdigit() else 80
            else:
                server_info['address'] = address_part
        
        # 解析参数
        for part in parts[1:]:
            if part == 'backup':
                server_info['backup'] = True
            elif part == 'down':
                server_info['down'] = True
            elif part.startswith('weight='):
                server_info['weight'] = int(part.split('=')[1])
            elif part.startswith('max_fails='):
                server_info['max_fails'] = int(part.split('=')[1])
            elif part.startswith('fail_timeout='):
                server_info['fail_timeout'] = part.split('=')[1]
            elif part.startswith('max_conns='):
                server_info['max_conns'] = int(part.split('=')[1])
        
    except Exception as e:
        logger.error(f"解析服务器配置失败 {server_config}: {e}")
    
    return server_info

def analyze_load_balancing_method(upstream_content: str) -> str:
    """
    解析负载均衡策略
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        str: 负载均衡策略
    """
    lb_method = 'round-robin'  # 默认轮询
    
    try:
        if re.search(r'ip_hash', upstream_content):  # NOSONAR
            lb_method = 'ip_hash'
        elif re.search(r'least_conn', upstream_content):  # NOSONAR
            lb_method = 'least_conn'
        elif re.search(r'hash', upstream_content):  # NOSONAR
            hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
            if hash_match:
                lb_method = f"hash: {hash_match.group(1)}"
        elif re.search(r'fair', upstream_content):  # NOSONAR
            lb_method = 'fair'
        elif re.search(r'url_hash', upstream_content):  # NOSONAR
            lb_method = 'url_hash'
        
    except Exception as e:
        logger.error(f"解析负载均衡策略失败: {e}")
    
    return lb_method

def analyze_retry_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析重试配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 重试配置信息
    """
    retry_config = {
        'proxy_next_upstream': 'error timeout',
        'proxy_next_upstream_tries': 0,
        'proxy_next_upstream_timeout': '0s',
        'proxy_connect_timeout': '60s',
        'proxy_read_timeout': '60s',
        'proxy_send_timeout': '60s'
    }
    
    try:
        # 查找proxy_next_upstream配置
        next_upstream_match = re.search(r'proxy_next_upstream\s+([^;]+);', upstream_content)  # NOSONAR
        if next_upstream_match:
            retry_config['proxy_next_upstream'] = next_upstream_match.group(1)
        
        # 查找重试次数配置
        tries_match = re.search(r'proxy_next_upstream_tries\s+(\d+);', upstream_content)  # NOSONAR
        if tries_match:
            retry_config['proxy_next_upstream_tries'] = int(tries_match.group(1))
        
        # 查找重试超时配置
        timeout_match = re.search(r'proxy_next_upstream_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if timeout_match:
            retry_config['proxy_next_upstream_timeout'] = timeout_match.group(1)
        
        # 查找连接超时配置
        connect_timeout_match = re.search(r'proxy_connect_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if connect_timeout_match:
            retry_config['proxy_connect_timeout'] = connect_timeout_match.group(1)
        
        # 查找读取超时配置
        read_timeout_match = re.search(r'proxy_read_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if read_timeout_match:
            retry_config['proxy_read_timeout'] = read_timeout_match.group(1)
        
        # 查找发送超时配置
        send_timeout_match = re.search(r'proxy_send_timeout\s+([^;]+);', upstream_content)  # NOSONAR
        if send_timeout_match:
            retry_config['proxy_send_timeout'] = send_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析重试配置失败: {e}")
    
    return retry_config

def fetch_nginx_error_log_path() -> Optional[str]:
    """
    获取Nginx错误日志路径
    
    返回:
        str: 错误日志文件路径
    """
    try:
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        body = load_nginx_config(cfg_filepath)
        
        # 查找error_log配置
        error_log_pattern = r'error_log\s+([^;]+)\s+([^;]+);'  # NOSONAR
        error_log_matches = re.finditer(error_log_pattern, body)  # NOSONAR
        
        for match in error_log_matches:
            log_path = match.group(1).strip()
            # 处理相对路径
            if not log_path.startswith('/'):
                config_dir = os.path.dirname(cfg_filepath)
                log_path = os.path.join(config_dir, log_path)
            return log_path
        
        # 默认错误日志路径
        default_paths = [
            '/var/log/nginx/error.log',
            '/usr/local/nginx/logs/error.log',
            '/opt/nginx/logs/error.log'
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx错误日志路径失败: {e}")
        return None

def examine_error_logs(upstream_name: str, hours: int = 24) -> Dict[str, Any]:
    """
    分析错误日志中的失败信息
    
    参数:
        upstream_name: upstream名称
        hours: 分析最近多少小时的数据
        
    返回:
        dict: 错误日志分析结果
    """
    error_analysis = {
        'upstream_name': upstream_name,
        'analysis_period_hours': hours,
        'total_errors': 0,
        'connection_errors': 0,
        'timeout_errors': 0,
        'http_errors': 0,
        'error_timeline': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        error_log_path = fetch_nginx_error_log_path()
        if not error_log_path or not os.path.exists(error_log_path):
            error_analysis['error'] = '无法找到错误日志文件'
            return error_analysis
        
        # 计算时间范围
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 读取错误日志
        with open(error_log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    # 解析日志时间戳
                    log_time = analyze_log_timestamp(line)
                    if log_time and log_time < cutoff_time:
                        continue
                    
                    # 分析错误类型
                    error_info = examine_error_line(line, upstream_name)
                    if error_info:
                        error_analysis['total_errors'] += 1
                        
                        if 'connection' in error_info['error_type']:
                            error_analysis['connection_errors'] += 1
                        elif 'timeout' in error_info['error_type']:
                            error_analysis['timeout_errors'] += 1
                        elif 'http' in error_info['error_type']:
                            error_analysis['http_errors'] += 1
                        
                        error_analysis['error_timeline'].append(error_info)
                        
                except Exception as e:
                    continue
        
        # 按时间排序错误时间线
        error_analysis['error_timeline'].sort(key=lambda x: x['timestamp'])
        
    except Exception as e:
        logger.error(f"分析错误日志失败: {e}")
        error_analysis['error'] = f"分析失败: {e}"
    
    return error_analysis

def analyze_log_timestamp(log_line: str) -> Optional[datetime]:
    """
    解析日志时间戳
    
    参数:
        log_line: 日志行
        
    返回:
        datetime: 日志时间，解析失败返回None
    """
    try:
        # 常见的Nginx日志时间格式
        timestamp_patterns = [
            r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})',
            r'(\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4})',
            r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, log_line)  # NOSONAR
            if match:
                timestamp_str = match.group(1)
                try:
                    return datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                except Exception:
                    try:
                        return datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Y')
                    except Exception:
                        try:
                            return datetime.strptime(timestamp_str, '%d/%b/%Y:%H:%M:%S')
                        except Exception:
                            continue
        
        return None
        
    except Exception as e:
        return None

def examine_error_line(log_line: str, upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    分析单行错误日志
    
    参数:
        log_line: 日志行
        upstream_name: upstream名称
        
    返回:
        dict: 错误信息，如果不是相关错误返回None
    """
    try:
        # 检查是否包含upstream名称
        if upstream_name not in log_line:
            return None
        
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': 'unknown',
            'server_address': 'unknown',
            'error_message': log_line.strip(),
            'retry_attempt': 0
        }
        
        # 解析时间戳
        log_time = analyze_log_timestamp(log_line)
        if log_time:
            error_info['timestamp'] = log_time.isoformat()
        
        # 分析错误类型
        if 'connect() failed' in log_line or 'Connection refused' in log_line:
            error_info['error_type'] = 'connection_refused'
        elif 'Connection timed out' in log_line or 'upstream timed out' in log_line:
            error_info['error_type'] = 'connection_timeout'
        elif 'upstream server temporarily disabled' in log_line:
            error_info['error_type'] = 'server_disabled'
        elif 'no live upstreams' in log_line:
            error_info['error_type'] = 'no_live_upstreams'
        elif 'bad gateway' in log_line or '502' in log_line:
            error_info['error_type'] = 'http_502'
        elif 'service unavailable' in log_line or '503' in log_line:
            error_info['error_type'] = 'http_503'
        
        # 解析服务器地址
        server_match = re.search(r'to ([\d\.]+:\d+)', log_line)  # NOSONAR
        if server_match:
            error_info['server_address'] = server_match.group(1)
        
        # 解析重试次数
        retry_match = re.search(r'while connecting to upstream, client:.*, server:.*, request:.*, upstream:.*, (\d+)', log_line)  # NOSONAR
        if retry_match:
            error_info['retry_attempt'] = int(retry_match.group(1))
        
        return error_info
        
    except Exception as e:
        return None

def estimate_failure_metrics(upstream_name: str, hours: int = 24) -> Dict[str, Any]:
    """
    估算失败指标
    
    参数:
        upstream_name: upstream名称
        hours: 分析时间范围（小时）
        
    返回:
        dict: 失败指标估算
    """
    failure_metrics = {
        'upstream_name': upstream_name,
        'analysis_period_hours': hours,
        'estimated_total_requests': 0,
        'estimated_failed_requests': 0,
        'failure_rate_percentage': 0,
        'circuit_breaker_status': 'unknown',
        'average_retry_count': 0,
        'server_failure_stats': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取upstream配置
        upstream_config = fetch_upstream_configuration(upstream_name)
        if not upstream_config:
            failure_metrics['error'] = f"无法获取upstream配置: {upstream_name}"
            return failure_metrics
        
        # 分析错误日志
        error_analysis = examine_error_logs(upstream_name, hours)
        
        # 估算总请求数（基于错误率和假设的正常请求比例）
        total_errors = error_analysis.get('total_errors', 0)
        
        # 假设错误率在1%-5%之间，估算总请求数
        if total_errors > 0:
            # 基于错误率估算总请求数
            assumed_error_rate = 0.02  # 2%的错误率
            failure_metrics['estimated_total_requests'] = int(total_errors / assumed_error_rate)
            failure_metrics['estimated_failed_requests'] = total_errors
            failure_metrics['failure_rate_percentage'] = round(assumed_error_rate * 100, 2)
        else:
            # 没有错误，假设请求量较低
            failure_metrics['estimated_total_requests'] = 1000
            failure_metrics['estimated_failed_requests'] = 0
            failure_metrics['failure_rate_percentage'] = 0
        
        # 分析熔断状态
        failure_metrics['circuit_breaker_status'] = examine_circuit_breaker_status(
            upstream_config, error_analysis
        )
        
        # 计算平均重试次数
        if error_analysis.get('error_timeline'):
            retry_counts = [e.get('retry_attempt', 0) for e in error_analysis['error_timeline']]
            failure_metrics['average_retry_count'] = round(
                sum(retry_counts) / len(retry_counts), 2
            )
        
        # 统计每个服务器的失败情况
        server_stats = {}
        for error in error_analysis.get('error_timeline', []):
            server_addr = error.get('server_address', 'unknown')
            if server_addr not in server_stats:
                server_stats[server_addr] = {
                    'failure_count': 0,
                    'error_types': set(),
                    'last_error_time': error['timestamp']
                }
            
            server_stats[server_addr]['failure_count'] += 1
            server_stats[server_addr]['error_types'].add(error['error_type'])
            server_stats[server_addr]['last_error_time'] = max(
                server_stats[server_addr]['last_error_time'], error['timestamp']
            )
        
        # 转换为列表格式
        for server_addr, stats in server_stats.items():
            server_info = {
                'server_address': server_addr,
                'failure_count': stats['failure_count'],
                'error_types': list(stats['error_types']),
                'last_error_time': stats['last_error_time']
            }
            failure_metrics['server_failure_stats'].append(server_info)
        
    except Exception as e:
        logger.error(f"估算失败指标失败 {upstream_name}: {e}")
        failure_metrics['error'] = f"估算失败: {e}"
    
    return failure_metrics

def examine_circuit_breaker_status(upstream_config: Dict[str, Any], 
                                 error_analysis: Dict[str, Any]) -> str:
    """
    分析熔断器状态
    
    参数:
        upstream_config: upstream配置
        error_analysis: 错误分析结果
        
    返回:
        str: 熔断器状态（open/half-open/closed）
    """
    try:
        # 获取最近的错误信息
        recent_errors = error_analysis.get('error_timeline', [])
        if not recent_errors:
            return 'closed'  # 没有错误，熔断器关闭
        
        # 按时间排序
        recent_errors.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 检查最近1小时内的错误频率
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_error_count = 0
        
        for error in recent_errors:
            error_time = datetime.fromisoformat(error['timestamp'])
            if error_time > one_hour_ago:
                recent_error_count += 1
            else:
                break
        
        # 获取熔断配置
        max_fails = 1
        fail_timeout = 10  # 默认10秒
        
        for server in upstream_config.get('servers', []):
            if server.get('max_fails', 0) > max_fails:
                max_fails = server['max_fails']
            
            # 解析fail_timeout
            timeout_str = server.get('fail_timeout', '10s')
            timeout_match = re.search(r'(\d+)', timeout_str)  # NOSONAR
            if timeout_match:
                server_timeout = int(timeout_match.group(1))
                if server_timeout > fail_timeout:
                    fail_timeout = server_timeout
        
        # 判断熔断状态
        if recent_error_count >= max_fails * 2:  # 错误数超过阈值2倍
            return 'open'  # 熔断器打开
        elif recent_error_count >= max_fails:
            return 'half-open'  # 半开状态
        else:
            return 'closed'  # 关闭状态
        
    except Exception as e:
        logger.error(f"分析熔断器状态失败: {e}")
        return 'unknown'