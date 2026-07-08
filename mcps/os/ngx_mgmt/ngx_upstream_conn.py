#!/usr/bin/env python3
"""
Nginx上游服务连接数统计工具
获取上游服务组的总连接数、活跃连接数、最大连接数等信息
"""

import os
import re
import json
import logging
import subprocess
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import psutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_connection')

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
        upstream_pattern = rf'upstream\s+{upstream_name}\s*{{([^}}]+)}}'
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
        
        return {
            'name': upstream_name,
            'servers': servers,
            'load_balancing_method': lb_method,
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

def fetch_nginx_status_info() -> Optional[Dict[str, Any]]:
    """
    获取Nginx状态信息（通过stub_status模块）
    
    返回:
        dict: Nginx状态信息
    """
    try:
        # 尝试获取状态模块URL
        status_url = fetch_nginx_status_module_url()
        if not status_url:
            return None
        
        import requests
        response = requests.get(status_url, timeout=10)
        if response.status_code == 200:
            return analyze_status_output(response.text)
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx状态信息失败: {e}")
        return None

def fetch_nginx_status_module_url() -> Optional[str]:
    """
    获取Nginx状态模块URL
    
    返回:
        str: 状态模块URL，如果未配置返回None
    """
    try:
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return None
        
        body = load_nginx_config(cfg_filepath)
        
        # 查找status模块配置
        status_pattern = r'location\s+/(\w+/)?status\s*\{[^}]+\}'  # NOSONAR
        status_matches = re.finditer(status_pattern, body, re.DOTALL)  # NOSONAR
        
        for match in status_matches:
            location_content = match.group(0)
            if 'stub_status' in location_content:
                # 获取监听的端口和地址
                server_pattern = r'listen\s+([^;]+);'  # NOSONAR
                server_matches = re.findall(server_pattern, body)  # NOSONAR
                
                for server_match in server_matches:
                    listen_config = server_match.strip()
                    port = listen_config.split(':')[1] if ':' in listen_config else listen_config
                    return f"http://127.0.0.1:{port}/status"  # NOSONAR
        
        # 常见状态模块URL
        common_urls = [
            "http://127.0.0.1:80/status",  # NOSONAR
            "http://127.0.0.1:8080/status",  # NOSONAR
            "http://localhost/nginx_status",  # NOSONAR
            "http://127.0.0.1/nginx_status"  # NOSONAR
        ]
        
        for url in common_urls:
            if verify_url_accessibility(url):
                return url
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx状态模块URL失败: {e}")
        return None

def verify_url_accessibility(url: str, timeout: int = 5) -> bool:
    """
    检查URL可访问性
    
    参数:
        url: 要检查的URL
        timeout: 超时时间（秒）
        
    返回:
        bool: 是否可访问
    """
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def analyze_status_output(status_text: str) -> Dict[str, Any]:
    """
    解析Nginx状态输出
    
    参数:
        status_text: 状态模块输出文本
        
    返回:
        dict: 解析后的状态信息
    """
    status_info = {
        'active_connections': 0,
        'server_accepts': 0,
        'server_handled': 0,
        'server_requests': 0,
        'reading': 0,
        'writing': 0,
        'waiting': 0
    }
    
    try:
        # 解析标准格式
        lines = status_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if 'Active connections:' in line:
                status_info['active_connections'] = int(line.split(':')[1].strip())
            elif 'server accepts handled requests' in line:
                parts = line.split()
                if len(parts) >= 4:
                    status_info['server_accepts'] = int(parts[3])
                    status_info['server_handled'] = int(parts[4])
                    status_info['server_requests'] = int(parts[5])
            elif 'Reading:' in line:
                parts = line.split()
                status_info['reading'] = int(parts[1])
                status_info['writing'] = int(parts[3])
                status_info['waiting'] = int(parts[5])
        
    except Exception as e:
        logger.error(f"解析状态输出失败: {e}")
    
    return status_info

def fetch_nginx_process_connections() -> Dict[str, Any]:
    """
    获取Nginx进程连接数信息
    
    返回:
        dict: 进程连接数信息
    """
    connection_info = {
        'total_connections': 0,
        'active_connections': 0,
        'idle_connections': 0,
        'process_count': 0,
        'worker_processes': []
    }
    
    try:
        # 查找Nginx进程
        nginx_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    nginx_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        connection_info['process_count'] = len(nginx_processes)
        
        # 分析每个进程的连接数
        for proc in nginx_processes:
            try:
                connections = proc.connections()
                worker_info = {
                    'pid': proc.pid,
                    'name': proc.name(),
                    'total_connections': len(connections),
                    'active_connections': len([c for c in connections if c.status == 'ESTABLISHED']),
                    'idle_connections': len([c for c in connections if c.status == 'LISTEN'])
                }
                
                connection_info['total_connections'] += worker_info['total_connections']
                connection_info['active_connections'] += worker_info['active_connections']
                connection_info['idle_connections'] += worker_info['idle_connections']
                connection_info['worker_processes'].append(worker_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
    except Exception as e:
        logger.error(f"获取Nginx进程连接数失败: {e}")
    
    return connection_info

def estimate_upstream_connections(upstream_name: str) -> Dict[str, Any]:
    """
    估算upstream连接数
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: 连接数估算信息
    """
    connection_estimate = {
        'upstream_name': upstream_name,
        'total_connections': 0,
        'active_connections': 0,
        'max_connections': 0,
        'connection_distribution': [],
        'estimation_method': 'calculated',
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取upstream配置
        upstream_config = fetch_upstream_configuration(upstream_name)
        if not upstream_config:
            connection_estimate['error'] = f"无法获取upstream配置: {upstream_name}"
            return connection_estimate
        
        # 获取Nginx状态信息
        nginx_status = fetch_nginx_status_info()
        process_connections = fetch_nginx_process_connections()
        
        # 计算总连接数
        if nginx_status:
            connection_estimate['total_connections'] = nginx_status['active_connections']
            connection_estimate['active_connections'] = nginx_status['active_connections'] - nginx_status['waiting']
        else:
            connection_estimate['total_connections'] = process_connections['total_connections']
            connection_estimate['active_connections'] = process_connections['active_connections']
        
        # 计算每个服务器的连接数分布
        total_weight = sum(server['weight'] for server in upstream_config['servers'] 
                          if not server['down'])
        
        if total_weight > 0:
            for server in upstream_config['servers']:
                if server['down']:
                    continue
                
                weight_ratio = server['weight'] / total_weight
                server_connections = {
                    'server_address': f"{server['address']}:{server['port']}",
                    'weight': server['weight'],
                    'estimated_connections': int(connection_estimate['total_connections'] * weight_ratio),
                    'max_connections': server.get('max_conns', 0),
                    'status': 'active' if not server.get('down', False) else 'down'
                }
                
                connection_estimate['connection_distribution'].append(server_connections)
                connection_estimate['max_connections'] += server_connections['max_connections']
        
        # 如果没有配置最大连接数，使用默认值
        if connection_estimate['max_connections'] == 0:
            connection_estimate['max_connections'] = len(upstream_config['servers']) * 1000  # 默认每个服务器1000连接
        
    except Exception as e:
        logger.error(f"估算upstream连接数失败 {upstream_name}: {e}")
        connection_estimate['error'] = f"估算失败: {e}"
    
    return connection_estimate

def fetch_upstream_connection_analysis(upstream_name: str) -> Dict[str, Any]:
    """
    分析upstream连接状态
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: 连接状态分析
    """
    analysis = {
        'upstream_name': upstream_name,
        'connection_health': 'unknown',
        'utilization_percentage': 0,
        'recommendations': [],
        'alerts': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取连接数估算
        connection_estimate = estimate_upstream_connections(upstream_name)
        
        if 'error' in connection_estimate:
            analysis['error'] = connection_estimate['error']
            return analysis
        
        # 计算利用率
        if connection_estimate['max_connections'] > 0:
            analysis['utilization_percentage'] = round(
                (connection_estimate['total_connections'] / connection_estimate['max_connections']) * 100, 2
            )
        
        # 判断连接健康状态
        if analysis['utilization_percentage'] > 90:
            analysis['connection_health'] = 'critical'
            analysis['alerts'].append('连接数利用率超过90%，接近最大限制')
        elif analysis['utilization_percentage'] > 70:
            analysis['connection_health'] = 'warning'
            analysis['alerts'].append('连接数利用率超过70%，需要关注')
        else:
            analysis['connection_health'] = 'healthy'
        
        # 生成建议
        if analysis['utilization_percentage'] > 80:
            analysis['recommendations'].append('考虑增加服务器数量或调整连接限制')
        
        if any(server['max_connections'] == 0 for server in connection_estimate['connection_distribution']):
            analysis['recommendations'].append('建议为服务器配置max_conns参数以限制连接数')
        
        # 检查连接分布是否均衡
        if len(connection_estimate['connection_distribution']) > 1:
            connections = [s['estimated_connections'] for s in connection_estimate['connection_distribution']]
            max_conn = max(connections)
            min_conn = min(connections)
            
            if max_conn > min_conn * 3:  # 最大连接数超过最小连接数的3倍
                analysis['recommendations'].append('连接分布不均衡，建议检查负载均衡配置')
        
    except Exception as e:
        logger.error(f"分析upstream连接状态失败: {e}")
        analysis['error'] = f"分析失败: {e}"
    
    return analysis

def fetch_all_upstreams_connection_summary() -> Dict[str, Any]:
    """
    获取所有upstream的连接数汇总
    
    返回:
        dict: 所有upstream连接数汇总信息
    """
    summary = {
        'total_upstreams': 0,
        'total_connections': 0,
        'total_active_connections': 0,
        'total_max_connections': 0,
        'upstreams_details': [],
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取所有upstream配置
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            summary['error'] = '无法找到Nginx配置文件'
            return summary
        
        body = load_nginx_config(cfg_filepath)
        upstream_pattern = r'upstream\s+(\w+)\s*\{[^}]+\}'  # NOSONAR
        upstream_matches = re.findall(upstream_pattern, body)  # NOSONAR
        
        if not upstream_matches:
            summary['message'] = '未找到任何upstream配置'
            return summary
        
        summary['total_upstreams'] = len(upstream_matches)
        
        # 获取每个upstream的连接信息
        for upstream_name in upstream_matches:
            connection_info = estimate_upstream_connections(upstream_name)
            if 'error' not in connection_info:
                summary['total_connections'] += connection_info['total_connections']
                summary['total_active_connections'] += connection_info['active_connections']
                summary['total_max_connections'] += connection_info['max_connections']
                
                upstream_detail = {
                    'name': upstream_name,
                    'total_connections': connection_info['total_connections'],
                    'active_connections': connection_info['active_connections'],
                    'max_connections': connection_info['max_connections'],
                    'utilization_percentage': round(
                        (connection_info['total_connections'] / connection_info['max_connections']) * 100, 2
                    ) if connection_info['max_connections'] > 0 else 0
                }
                summary['upstreams_details'].append(upstream_detail)
        
    except Exception as e:
        logger.error(f"获取所有upstream连接汇总失败: {e}")
        summary['error'] = f"汇总失败: {e}"
    
    return summary

def fetch_nginx_upstream_connection(upstream_name: str = "") -> str:
    """
    获取Nginx上游服务连接数信息
    
    参数:
        upstream_name: upstream名称（可选，为空时获取所有upstream连接数汇总）
        
    返回:
        str: JSON格式的上游服务连接数信息
    """
    try:
        # 检查Nginx是否运行
        nginx_running = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                nginx_running = True
                break
        
        if not nginx_running:
            return json.dumps({
                'status': 'error',
                'message': 'Nginx服务未运行',
                'suggestion': '请先启动Nginx服务',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 根据是否指定upstream_name返回不同信息
        if upstream_name:
            # 获取指定upstream的连接信息
            connection_info = estimate_upstream_connections(upstream_name)
            connection_analysis = fetch_upstream_connection_analysis(upstream_name)
            
            output = {
                'status': 'success',
                'upstream_name': upstream_name,
                'connection_info': connection_info,
                'connection_analysis': connection_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
            if 'error' in connection_info:
                output['status'] = 'error'
                output['message'] = connection_info['error']
            
        else:
            # 获取所有upstream的连接汇总
            summary = fetch_all_upstreams_connection_summary()
            output = {
                'status': 'success',
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            }
            
            if 'error' in summary:
                output['status'] = 'error'
                output['message'] = summary['error']
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取Nginx上游连接数失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'获取连接数失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

# 工具配置
TOOL_CONFIG = {
    'name': 'fetch_nginx_upstream_connection',
    'description': '获取Nginx配置文件中定义的所有上游服务的连接数信息，包括总连接数、活跃连接数、最大连接数等',
    'category': 'Nginx',
    'function': fetch_nginx_upstream_connection,
    'output_format': 'json'
}