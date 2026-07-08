#!/usr/bin/env python3
"""
Nginx上游服务器失败统计清零和熔断状态重置工具
支持清空上游服务器的失败请求统计、重置熔断状态、恢复故障服务器
"""

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_clear')

def verify_nginx_installation() -> Dict[str, Any]:
    """
    检查Nginx是否安装
    
    返回:
        dict: 包含安装状态和信息的字典
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        if output.returncode == 0:
            return {
                'installed': True,
                'version': output.stderr.strip() if output.stderr else 'Unknown',
                'suggestion': 'Nginx已正确安装'
            }
        else:
            return {
                'installed': False,
                'version': 'Unknown',
                'suggestion': '请先安装Nginx或检查PATH环境变量'
            }
    except Exception as e:
        return {
            'installed': False,
            'version': 'Unknown',
            'suggestion': f'检查Nginx安装失败: {e}'
        }

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

def fetch_nginx_process_info() -> Optional[Dict[str, Any]]:
    """
    获取Nginx进程信息
    
    返回:
        dict: Nginx进程信息
    """
    try:
        nginx_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    nginx_processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                        'status': proc.status()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            'process_count': len(nginx_processes),
            'processes': nginx_processes,
            'master_pid': nginx_processes[0]['pid'] if nginx_processes else None
        }
        
    except Exception as e:
        logger.error(f"获取Nginx进程信息失败: {e}")
        return None

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
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 查找指定的upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
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
                lb_method = f'hash {hash_match.group(1)}'
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
        'max_fails': 1,
        'fail_timeout': '10s',
        'proxy_next_upstream': 'error timeout',
        'proxy_next_upstream_tries': 0,
        'proxy_next_upstream_timeout': 0
    }
    
    try:
        # 解析max_fails和fail_timeout（在server级别）
        max_fails_match = re.search(r'max_fails=(\d+)', upstream_content)  # NOSONAR
        if max_fails_match:
            retry_config['max_fails'] = int(max_fails_match.group(1))
        
        fail_timeout_match = re.search(r'fail_timeout=([\d]+[smh]?)', upstream_content)  # NOSONAR
        if fail_timeout_match:
            retry_config['fail_timeout'] = fail_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析重试配置失败: {e}")
    
    return retry_config

def fetch_upstream_status_from_nginx_plus(upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    从Nginx Plus获取upstream状态（商业版功能）
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: upstream状态信息
    """
    try:
        # Nginx Plus状态API
        status_urls = [
            f"http://127.0.0.1:8080/api/3/http/upstreams/{upstream_name}/peers",  # NOSONAR
            f"http://127.0.0.1:80/api/3/http/upstreams/{upstream_name}/peers"  # NOSONAR
        ]
        
        for url in status_urls:
            if verify_url_accessibility(url):
                import requests
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()
        
        return None
        
    except Exception as e:
        logger.error(f"从Nginx Plus获取状态失败: {e}")
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

def clear_upstream_fail_stats_nginx_plus(upstream_name: str, server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    通过Nginx Plus API清空失败统计（商业版功能）
    
    参数:
        upstream_name: upstream名称
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'cleared_servers': []
    }
    
    try:
        # 获取当前状态
        status_data = fetch_upstream_status_from_nginx_plus(upstream_name)
        if not status_data:
            output['message'] = "无法获取Nginx Plus状态信息"
            return output
        
        # 构建清空请求
        clear_urls = [
            f"http://127.0.0.1:8080/api/3/http/upstreams/{upstream_name}/peers",  # NOSONAR
            f"http://127.0.0.1:80/api/3/http/upstreams/{upstream_name}/peers"  # NOSONAR
        ]
        
        import requests
        
        for url in clear_urls:
            if verify_url_accessibility(url):
                # 获取所有服务器
                response = requests.get(url)
                if response.status_code == 200:
                    peers = response.json()
                    
                    for peer in peers:
                        peer_id = peer.get('id')
                        peer_addr = peer.get('server')
                        
                        # 如果指定了特定服务器，只处理该服务器
                        if server_address and server_address not in peer_addr:
                            continue
                        
                        # 发送清空请求
                        clear_url = f"{url}/{peer_id}/state"
                        clear_data = {
                            'fails': 0,
                            'unavailable': None
                        }
                        
                        clear_response = requests.patch(clear_url, json=clear_data)
                        if clear_response.status_code == 200:
                            output['cleared_servers'].append(peer_addr)
                    
                    if output['cleared_servers']:
                        output['success'] = True
                        output['message'] = f"成功清空 {len(output['cleared_servers'])} 个服务器的失败统计"
                    else:
                        output['message'] = "未找到匹配的服务器"
                    
                    return output
        
        output['message'] = "Nginx Plus API不可用"
        return output
        
    except Exception as e:
        logger.error(f"清空Nginx Plus失败统计失败: {e}")
        output['message'] = f"清空失败: {e}"
        return output

def clear_upstream_circuit_breaker(upstream_name: str, server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    重置熔断器状态
    
    参数:
        upstream_name: upstream 名称
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'reset_servers': []
    }
    
    try:
        # 安全验证：验证 upstream_name 标识符参数
        valid, error_msg = validate_identifier_param(upstream_name)
        if not valid:
            logger.error(f"clear_upstream_circuit_breaker: upstream_name 验证失败：{error_msg}")
            output['message'] = f'无效的 upstream 名称：{error_msg}'
            return output
        
        # 安全验证：如果提供 server_address，也进行验证
        if server_address is not None:
            valid, error_msg = validate_identifier_param(server_address)
            if not valid:
                logger.error(f"clear_upstream_circuit_breaker: server_address 验证失败：{error_msg}")
                output['message'] = f'无效的服务器地址：{error_msg}'
                return output
        
        # 方法 1: 通过 Nginx Plus API（商业版）
        plus_result = clear_upstream_fail_stats_nginx_plus(upstream_name, server_address)
        if plus_result['success']:
            return plus_result
        
        # 方法 2: 通过重新加载配置（开源版）
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            output['message'] = "无法获取 Nginx 配置文件路径"
            return output
        
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"clear_upstream_circuit_breaker: cfg_filepath 路径验证失败：{error_msg}")
            output['message'] = f'配置文件路径不安全：{error_msg}'
            return output
        
        # 备份配置文件
        backup_path = f"{cfg_filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        subprocess.run(['cp', cfg_filepath, backup_path], check=True)
        
        # 读取配置内容
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 查找upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
        upstream_match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not upstream_match:
            output['message'] = f"未找到upstream配置: {upstream_name}"
            return output
        
        upstream_content = upstream_match.group(1)
        upstream_start = upstream_match.start(1)
        upstream_end = upstream_match.end(1)
        
        # 修改服务器配置，移除down标记
        new_upstream_content = upstream_content
        
        # 处理每个服务器
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = list(re.finditer(server_pattern, upstream_content))  # NOSONAR
        
        for match in reversed(server_matches):  # 从后往前处理，避免位置偏移
            server_config = match.group(1).strip()
            server_parts = server_config.split()
            
            # 如果指定了特定服务器，只处理该服务器
            if server_address and server_address not in server_parts[0]:
                continue
            
            # 移除down标记
            new_server_config = ' '.join([part for part in server_parts if part != 'down'])
            
            # 替换服务器配置
            new_upstream_content = (new_upstream_content[:match.start(1)] + 
                                  new_server_config + 
                                  new_upstream_content[match.end(1):])
            
            output['reset_servers'].append(server_parts[0])
        
        if not output['reset_servers']:
            output['message'] = "未找到匹配的服务器"
            return output
        
        # 替换整个upstream内容
        new_content = body[:upstream_start] + new_upstream_content + body[upstream_end:]
        
        # 写回配置文件
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 检查配置语法
        syntax_check = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if syntax_check.returncode != 0:
            # 恢复备份
            subprocess.run(['cp', backup_path, cfg_filepath], check=True)
            output['message'] = f"配置语法错误: {syntax_check.stderr}"
            return output
        
        # 重新加载配置
        reload_result = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)
        if reload_result.returncode == 0:
            output['success'] = True
            output['message'] = f"成功重置 {len(output['reset_servers'])} 个服务器的熔断状态"
        else:
            output['message'] = f"重新加载配置失败: {reload_result.stderr}"
        
        return output
        
    except Exception as e:
        logger.error(f"重置熔断器状态失败: {e}")
        output['message'] = f"重置失败: {e}"
        return output

def recover_failed_server(upstream_name: str, server_address: str) -> Dict[str, Any]:
    """
    恢复故障服务器
    
    参数:
        upstream_name: upstream名称
        server_address: 服务器地址
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'restored_server': server_address
    }
    
    try:
        # 先重置熔断状态
        reset_result = clear_upstream_circuit_breaker(upstream_name, server_address)
        
        if reset_result['success']:
            output['success'] = True
            output['message'] = f"成功恢复服务器: {server_address}"
        else:
            output['message'] = reset_result['message']
        
        return output
        
    except Exception as e:
        logger.error(f"恢复故障服务器失败: {e}")
        output['message'] = f"恢复失败: {e}"
        return output

def clear_upstream_fail_stats(upstream_name: str, operation_type: str = 'reset_circuit_breaker', 
                             server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    清空上游服务器失败统计的主函数
    
    参数:
        upstream_name: upstream名称
        operation_type: 操作类型 ('reset_circuit_breaker', 'clear_fail_stats', 'restore_server')
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果信息
    """
    output = {
        'success': False,
        'message': '',
        'operation': operation_type,
        'upstream_name': upstream_name,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 检查Nginx安装
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            output['message'] = f"Nginx未安装: {nginx_check['suggestion']}"
            return output
        
        # 检查upstream配置是否存在
        upstream_config = fetch_upstream_configuration(upstream_name)
        if not upstream_config:
            output['message'] = f"未找到upstream配置: {upstream_name}"
            return output
        
        # 根据操作类型执行相应操作
        if operation_type == 'reset_circuit_breaker':
            reset_result = clear_upstream_circuit_breaker(upstream_name, server_address)
            output.update(reset_result)
            
        elif operation_type == 'clear_fail_stats':
            # 尝试使用Nginx Plus API
            clear_result = clear_upstream_fail_stats_nginx_plus(upstream_name, server_address)
            if not clear_result['success']:
                # 开源版本通过重置熔断器来间接清空统计
                clear_result = clear_upstream_circuit_breaker(upstream_name, server_address)
                clear_result['message'] = "开源版本通过重置熔断状态间接清空失败统计"
            output.update(clear_result)
            
        elif operation_type == 'restore_server':
            if not server_address:
                output['message'] = "恢复服务器操作需要指定server_address参数"
                return output
            restore_result = recover_failed_server(upstream_name, server_address)
            output.update(restore_result)
            
        else:
            output['message'] = f"不支持的操作类型: {operation_type}"
        
    except Exception as e:
        logger.error(f"清空上游失败统计失败: {e}")
        output['message'] = f"操作失败: {e}"
    
    return output

# MCP工具配置
TOOL_CONFIG = {
    "name": "clear_upstream_fail_stats",
    "function": clear_upstream_fail_stats,
    "description": "清空上游服务器的失败请求统计、重置熔断状态、恢复故障服务器",
    "version": "1.0.0",
    "parameters": {
        "type": "object",
        "properties": {
            "upstream_name": {
                "type": "string",
                "description": "上游服务器名称",
                "default": ""
            },
            "operation_type": {
                "type": "string",
                "enum": ["reset_circuit_breaker", "clear_fail_stats", "restore_server"],
                "description": "操作类型",
                "default": "reset_circuit_breaker"
            },
            "server_address": {
                "type": "string",
                "description": "特定服务器地址（可选，用于恢复单个服务器）",
                "default": ""
            }
        },
        "required": ["upstream_name"]
    },
    "examples": [
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "backend",
                "operation_type": "reset_circuit_breaker"
            }
        },
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "api_servers",
                "operation_type": "clear_fail_stats"
            }
        },
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "backend",
                "operation_type": "restore_server",
                "server_address": "192.168.1.100:8080"  # NOSONAR
            }
        }
    ]
}