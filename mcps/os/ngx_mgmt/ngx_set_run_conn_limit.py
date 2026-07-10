#!/usr/bin/env python3
"""
Nginx运行时连接限制管理工具
设置最大连接数、单IP最大连接数、连接队列长度等连接限制参数
"""

import os
import re
import json
import logging
import subprocess
import shutil
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, fetch_nginx_config_path, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_connect_limit')

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
    读取 Nginx 配置文件内容
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 配置文件内容
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"load_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return ""
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Nginx配置文件失败: {e}")
        return ""

def fetch_current_connection_settings(config_content: str) -> Dict[str, Any]:
    """
    获取当前连接限制设置
    
    参数:
        config_content: 配置文件内容
        
    返回:
        dict: 当前连接设置信息
    """
    settings = {
        'worker_connections': 512,  # 默认值
        'worker_rlimit_nofile': None,
        'multi_accept': 'off',
        'accept_mutex': 'on',
        'accept_mutex_delay': '500ms',
        'listen_backlog': 511,
        'keepalive_timeout': '75s',
        'keepalive_requests': 100,
        'client_max_body_size': '1m',
        'client_body_timeout': '60s',
        'client_header_timeout': '60s',
        'send_timeout': '60s',
        'limit_conn_zone': {},
        'limit_conn': {},
        'limit_req_zone': {},
        'limit_req': {}
    }
    
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 解析events块中的连接设置
        events_pattern = r'events\s*\{([^}]+)\}'  # NOSONAR
        events_match = re.search(events_pattern, body, re.DOTALL)  # NOSONAR
        
        if events_match:
            events_content = events_match.group(1)
            
            # 解析worker_connections
            worker_conn_match = re.search(r'worker_connections\s+(\d+);', events_content)  # NOSONAR
            if worker_conn_match:
                settings['worker_connections'] = int(worker_conn_match.group(1))
            
            # 解析其他events设置
            events_settings = {
                'multi_accept': r'multi_accept\s+(\w+);',
                'accept_mutex': r'accept_mutex\s+(\w+);',
                'accept_mutex_delay': r'accept_mutex_delay\s+([^;]+);',
                'use': r'use\s+([^;]+);'
            }
            
            for key, pattern in events_settings.items():
                match = re.search(pattern, events_content)  # NOSONAR
                if match:
                    settings[key] = match.group(1).strip()
        
        # 解析主配置中的连接相关设置
        main_settings = {
            'worker_rlimit_nofile': r'worker_rlimit_nofile\s+(\d+);',
            'listen_backlog': r'listen\s+[^;]+backlog=(\d+)[^;]*;',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);',
            'keepalive_requests': r'keepalive_requests\s+(\d+);',
            'client_max_body_size': r'client_max_body_size\s+([^;]+);',
            'client_body_timeout': r'client_body_timeout\s+([^;]+);',
            'client_header_timeout': r'client_header_timeout\s+([^;]+);',
            'send_timeout': r'send_timeout\s+([^;]+);'
        }
        
        for key, pattern in main_settings.items():
            match = re.search(pattern, body)  # NOSONAR
            if match:
                if key in ['keepalive_requests']:
                    settings[key] = int(match.group(1))
                elif key in ['listen_backlog']:
                    settings[key] = int(match.group(1))
                else:
                    settings[key] = match.group(1).strip()
        
        # 解析连接限制配置
        settings.update(analyze_connection_limits(body))
        
    except Exception as e:
        logger.error(f"获取当前连接设置失败: {e}")
    
    return settings

def analyze_connection_limits(config_content: str) -> Dict[str, Any]:
    """
    解析连接限制配置
    
    参数:
        config_content: 配置文件内容
        
    返回:
        dict: 连接限制配置
    """
    limits = {
        'limit_conn_zone': {},
        'limit_conn': {},
        'limit_req_zone': {},
        'limit_req': {}
    }
    
    try:
        # 解析limit_conn_zone
        conn_zone_pattern = r'limit_conn_zone\s+(\$[^\s]+)\s+zone=([^:]+):(\d+)(?:\s+rate=([^\s;]+))?;'  # NOSONAR
        conn_zone_matches = re.finditer(conn_zone_pattern, config_content)  # NOSONAR
        
        for match in conn_zone_matches:
            variable = match.group(1)
            zone_name = match.group(2)
            zone_size = match.group(3)
            rate = match.group(4) if match.group(4) else None
            
            limits['limit_conn_zone'][zone_name] = {
                'variable': variable,
                'size': zone_size,
                'rate': rate
            }
        
        # 解析limit_conn
        limit_conn_pattern = r'limit_conn\s+([^\s;]+)\s+(\d+);'  # NOSONAR
        limit_conn_matches = re.finditer(limit_conn_pattern, config_content)  # NOSONAR
        
        for match in limit_conn_matches:
            zone_name = match.group(1)
            max_conn = match.group(2)
            limits['limit_conn'][zone_name] = max_conn
        
        # 解析limit_req_zone
        req_zone_pattern = r'limit_req_zone\s+(\$[^\s]+)\s+zone=([^:]+):(\d+)(?:\s+rate=([^\s;]+))?;'  # NOSONAR
        req_zone_matches = re.finditer(req_zone_pattern, config_content)  # NOSONAR
        
        for match in req_zone_matches:
            variable = match.group(1)
            zone_name = match.group(2)
            zone_size = match.group(3)
            rate = match.group(4) if match.group(4) else None
            
            limits['limit_req_zone'][zone_name] = {
                'variable': variable,
                'size': zone_size,
                'rate': rate
            }
        
        # 解析limit_req
        limit_req_pattern = r'limit_req\s+(?:zone=([^\s;]+)|burst=(\d+)|nodelay)?(?:\s+zone=([^\s;]+)|burst=(\d+)|nodelay)?(?:\s+zone=([^\s;]+)|burst=(\d+)|nodelay)?;'  # NOSONAR
        limit_req_matches = re.finditer(limit_req_pattern, config_content)  # NOSONAR
        
        for match in limit_req_matches:
            zone_name = match.group(1) or match.group(3) or match.group(5)
            burst = match.group(2) or match.group(4) or match.group(6)
            nodelay = 'nodelay' in match.group(0)
            
            if zone_name:
                limits['limit_req'][zone_name] = {
                    'burst': burst,
                    'nodelay': nodelay
                }
        
    except Exception as e:
        logger.error(f"解析连接限制配置失败: {e}")
    
    return limits

def fetch_system_connection_info() -> Dict[str, Any]:
    """
    获取系统连接信息
    
    返回:
        dict: 系统连接信息
    """
    sys_info = {
        'file_descriptor_limit': 0,
        'current_open_files': 0,
        'tcp_connections': 0,
        'memory_available': 0,
        'cpu_cores': 0,
        'recommended_worker_connections': 0,
        'recommended_file_limit': 0
    }
    
    try:
        import resource
        
        # 获取文件描述符限制
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        sys_info['file_descriptor_limit'] = soft_limit
        
        # 获取当前打开文件数
        try:
            output = subprocess.run(['lsof', '-u', str(os.getuid())], capture_output=True, text=True)
            if output.returncode == 0:
                sys_info['current_open_files'] = len(output.stdout.strip().split('\n')) - 1
        except Exception:
            pass
        
        # 获取TCP连接数
        try:
            output = subprocess.run(['ss', '-t', '-a'], capture_output=True, text=True)
            if output.returncode == 0:
                sys_info['tcp_connections'] = len(output.stdout.strip().split('\n')) - 1
        except Exception:
            pass
        
        # 获取内存信息
        try:
            mem_data = psutil.virtual_memory()
            sys_info['memory_available'] = mem_data.available
        except Exception:
            pass
        
        # 获取CPU核心数
        sys_info['cpu_cores'] = os.cpu_count() or 1
        
        # 计算推荐值
        # 推荐worker_connections：文件描述符限制的70%除以CPU核心数
        if sys_info['file_descriptor_limit'] > 0:
            recommended = int((sys_info['file_descriptor_limit'] * 0.7) / sys_info['cpu_cores'])
            sys_info['recommended_worker_connections'] = min(recommended, 65535)
        
        # 推荐文件描述符限制：worker_connections * CPU核心数 * 1.5
        sys_info['recommended_file_limit'] = sys_info['recommended_worker_connections'] * sys_info['cpu_cores'] * 1.5
        
    except Exception as e:
        logger.error(f"获取系统连接信息失败: {e}")
    
    return sys_info

def certify_connection_settings(worker_connections: int, 
                               single_ip_limit: Optional[int] = None,
                               listen_backlog: Optional[int] = None) -> Tuple[bool, str]:
    """
    验证连接设置的有效性
    
    参数:
        worker_connections: 工作连接数
        single_ip_limit: 单IP连接限制
        listen_backlog: 监听队列长度
        
    返回:
        tuple: (是否有效, 错误信息)
    """
    try:
        # 验证worker_connections
        if worker_connections <= 0:
            return False, "工作连接数必须大于0"
        if worker_connections > 65535:
            return False, "工作连接数不能超过65535"
        
        # 验证单IP限制
        if single_ip_limit is not None:
            if single_ip_limit <= 0:
                return False, "单IP连接限制必须大于0"
            if single_ip_limit > worker_connections:
                return False, "单IP连接限制不能超过工作连接数"
        
        # 验证监听队列长度
        if listen_backlog is not None:
            if listen_backlog < 0:
                return False, "监听队列长度不能为负数"
            if listen_backlog > 65535:
                return False, "监听队列长度不能超过65535"
        
        return True, "设置有效"
        
    except Exception as e:
        return False, f"验证失败: {e}"

def modify_connection_settings(cfg_filepath: str, 
                             worker_connections: int,
                             single_ip_limit: Optional[int] = None,
                             listen_backlog: Optional[int] = None,
                             worker_rlimit_nofile: Optional[int] = None) -> Tuple[bool, str]:
    """
    更新 Nginx 连接设置
    
    参数:
        cfg_filepath: 配置文件路径
        worker_connections: 工作连接数
        single_ip_limit: 单 IP 连接限制（可选）
        listen_backlog: 监听队列长度（可选）
        worker_rlimit_nofile: 文件描述符限制（可选）
        
    返回:
        tuple: (是否成功，错误信息)
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"modify_connection_settings: cfg_filepath 路径验证失败：{error_msg}")
            return False, f"配置文件路径不安全：{error_msg}"
        
        # 读取原始配置
        original_content = Path(cfg_filepath).read_text(encoding='utf-8')
        
        # 创建备份
        backup_path = f"{cfg_filepath}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(cfg_filepath, backup_path)
        logger.info(f"配置文件已备份到: {backup_path}")
        
        # 更新配置内容
        updated_content = original_content
        
        # 更新worker_connections（在events块中）
        worker_conn_pattern = r'(events\s*\{[^}]*?)(worker_connections\s+[^;]+;)'  # NOSONAR
        worker_conn_replacement = f'\\1worker_connections {worker_connections};'
        
        if re.search(worker_conn_pattern, updated_content, re.DOTALL):  # NOSONAR
            updated_content = re.sub(worker_conn_pattern, worker_conn_replacement, updated_content, flags=re.DOTALL)  # NOSONAR
        else:
            # 在events块内插入
            events_pattern = r'(events\s*\{)([^}]*)(\})'  # NOSONAR
            events_match = re.search(events_pattern, updated_content, re.DOTALL)  # NOSONAR
            if events_match:
                replacement = f'{events_match.group(1)}{events_match.group(2)}    worker_connections {worker_connections};\n{events_match.group(3)}'
                updated_content = re.sub(events_pattern, replacement, updated_content, flags=re.DOTALL)  # NOSONAR
            else:
                # 创建events块
                events_block = f'events {{\n    worker_connections {worker_connections};\n    use epoll;\n    multi_accept on;\n}}\n\n'
                # 在http块之前插入
                http_pattern = r'http\s*\{'  # NOSONAR
                if re.search(http_pattern, updated_content):  # NOSONAR
                    updated_content = re.sub(http_pattern, f'{events_block}http {{', updated_content)  # NOSONAR
                else:
                    # 在文件开头插入
                    updated_content = f'{events_block}{updated_content}'
        
        # 更新worker_rlimit_nofile
        if worker_rlimit_nofile:
            rlimit_pattern = r'worker_rlimit_nofile\s+[^;]+;'  # NOSONAR
            rlimit_replacement = f'worker_rlimit_nofile {worker_rlimit_nofile};'
            
            if re.search(rlimit_pattern, updated_content):  # NOSONAR
                updated_content = re.sub(rlimit_pattern, rlimit_replacement, updated_content)  # NOSONAR
            else:
                # 在worker_processes之后插入
                worker_proc_pattern = r'(worker_processes\s+[^;]+;\n)'  # NOSONAR
                worker_proc_match = re.search(worker_proc_pattern, updated_content)  # NOSONAR
                if worker_proc_match:
                    replacement = f'{worker_proc_match.group(1)}worker_rlimit_nofile {worker_rlimit_nofile};\n'
                    updated_content = re.sub(worker_proc_pattern, replacement, updated_content)  # NOSONAR
        
        # 更新单IP连接限制
        if single_ip_limit:
            # 添加或更新limit_conn_zone
            conn_zone_name = 'perip'
            conn_zone_pattern = r'limit_conn_zone\s+\$binary_remote_addr\s+zone=perip:[^;]+;'  # NOSONAR
            conn_zone_replacement = f'limit_conn_zone $binary_remote_addr zone={conn_zone_name}:10m;'
            
            if re.search(conn_zone_pattern, updated_content):  # NOSONAR
                updated_content = re.sub(conn_zone_pattern, conn_zone_replacement, updated_content)  # NOSONAR
            else:
                # 在http块开始处插入
                http_start_pattern = r'(http\s*\{)'  # NOSONAR
                http_start_match = re.search(http_start_pattern, updated_content)  # NOSONAR
                if http_start_match:
                    replacement = f'{http_start_match.group(1)}\n    limit_conn_zone $binary_remote_addr zone={conn_zone_name}:10m;'
                    updated_content = re.sub(http_start_pattern, replacement, updated_content)  # NOSONAR
            
            # 添加或更新limit_conn
            limit_conn_pattern = r'limit_conn\s+perip\s+[^;]+;'  # NOSONAR
            limit_conn_replacement = f'limit_conn {conn_zone_name} {single_ip_limit};'
            
            if re.search(limit_conn_pattern, updated_content):  # NOSONAR
                updated_content = re.sub(limit_conn_pattern, limit_conn_replacement, updated_content)  # NOSONAR
            else:
                # 在server块内插入
                server_pattern = r'(server\s*\{[^}]*)(\})'  # NOSONAR
                server_match = re.search(server_pattern, updated_content, re.DOTALL)  # NOSONAR
                if server_match:
                    replacement = f'{server_match.group(1)}    limit_conn {conn_zone_name} {single_ip_limit};\n{server_match.group(2)}'
                    updated_content = re.sub(server_pattern, replacement, updated_content, flags=re.DOTALL)  # NOSONAR
        
        # 更新监听队列长度
        if listen_backlog:
            # 更新现有的listen指令
            listen_pattern = r'(listen\s+[^;]+)(;|$)'  # NOSONAR
            def add_backlog(match):
                listen_config = match.group(1)
                if 'backlog=' in listen_config:
                    return re.sub(r'backlog=\d+', f'backlog={listen_backlog}', listen_config) + match.group(2)  # NOSONAR
                return f'{listen_config} backlog={listen_backlog}' + match.group(2)
            
            updated_content = re.sub(listen_pattern, add_backlog, updated_content)  # NOSONAR
        
        # 写入更新后的配置
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # 验证配置语法
        validation_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if validation_result.returncode != 0:
            # 恢复备份
            shutil.copy2(backup_path, cfg_filepath)
            return False, f"配置语法错误: {validation_result.stderr}"
        
        return True, "配置更新成功"
        
    except Exception as e:
        logger.error(f"更新Nginx连接设置失败: {e}")
        return False, f"更新配置失败: {e}"

def reload_nginx_gracefully() -> Tuple[bool, str]:
    """
    平滑重载Nginx配置
    
    返回:
        tuple: (是否成功, 错误信息)
    """
    try:
        # 查找Nginx主进程
        output = subprocess.run(['pgrep', '-f', 'nginx.*master'], capture_output=True, text=True)
        if output.returncode != 0:
            return False, "Nginx主进程未找到"
        
        master_pid = output.stdout.strip().split('\n')[0]
        
        # 发送HUP信号给主进程
        output = subprocess.run(['kill', '-HUP', master_pid], capture_output=True, text=True)
        
        return True, "Nginx配置已平滑重载" if output.returncode == 0 else False, f"重载失败: {output.stderr}"
    except Exception as e:
        logger.error(f"平滑重载Nginx失败: {e}")
        return False, f"重载失败: {e}"

def set_nginx_connection_limits(worker_connections: int,
                               single_ip_limit: Optional[int] = None,
                               listen_backlog: Optional[int] = None,
                               worker_rlimit_nofile: Optional[int] = None,
                               reload_method: str = 'graceful') -> Dict[str, Any]:
    """
    设置Nginx连接限制的主函数
    
    参数:
        worker_connections: 工作连接数
        single_ip_limit: 单IP连接限制（可选）
        listen_backlog: 监听队列长度（可选）
        worker_rlimit_nofile: 文件描述符限制（可选）
        reload_method: 重载方式 ('graceful'平滑重载 或 'restart'重启)
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'previous_settings': {},
        'new_settings': {},
        'system_info': {},
        'reload_method': reload_method,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 验证输入参数
        is_valid, validation_msg = certify_connection_settings(
            worker_connections, single_ip_limit, listen_backlog
        )
        if not is_valid:
            output['message'] = f"无效的连接设置: {validation_msg}"
            return output
        
        # 获取配置文件路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            output['message'] = '无法找到Nginx配置文件'
            return output
        
        # 读取当前配置
        config_content = load_nginx_config(cfg_filepath)
        if not config_content:
            output['message'] = '无法读取Nginx配置文件'
            return output
        
        # 获取当前设置和系统信息
        output['previous_settings'] = fetch_current_connection_settings(config_content)
        output['system_info'] = fetch_system_connection_info()
        
        # 更新配置
        update_success, update_msg = modify_connection_settings(
            cfg_filepath, worker_connections, single_ip_limit, listen_backlog, worker_rlimit_nofile
        )
        
        if not update_success:
            output['message'] = update_msg
            return output
        
        # 应用新配置
        if reload_method == 'graceful':
            reload_success, reload_msg = reload_nginx_gracefully()
        else:
            # 重启Nginx
            reload_success, reload_msg = resume_nginx()
        
        if not reload_success:
            output['message'] = f"配置更新成功，但{reload_msg}"
            return output
        
        # 获取新设置
        new_config_content = load_nginx_config(cfg_filepath)
        output['new_settings'] = fetch_current_connection_settings(new_config_content)
        
        output['success'] = True
        output['message'] = f"连接限制设置已成功更新，并已{reload_msg}"
        
    except Exception as e:
        logger.error(f"设置Nginx连接限制失败: {e}")
        output['message'] = f"操作失败: {e}"
    
    return output