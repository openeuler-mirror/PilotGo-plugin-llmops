#!/usr/bin/env python3
"""
Nginx上游服务配置设置工具
设置上游服务的负载均衡策略、超时时间、重试次数、熔断阈值等配置参数
"""

import os
import re
import logging
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_config')

def verify_nginx_installed() -> bool:
    """
    检查Nginx是否安装
    
    返回:
        bool: 是否安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception as e:
        logger.error(f"检查Nginx安装状态失败: {e}")
        return False

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

def locate_upstream_block(upstream_name: str, config_content: str) -> Tuple[Optional[str], int, int]:
    """
    查找上游服务配置块
    
    参数:
        upstream_name: 上游服务名称
        config_content: 配置文件内容
        
    返回:
        tuple: (配置块内容, 起始位置, 结束位置)
    """
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 匹配指定的upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
        match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        upstream_content = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        return upstream_content, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找上游服务配置块失败: {e}")
        return None, -1, -1

def analyze_existing_upstream_config(upstream_content: str) -> Dict[str, Any]:
    """
    解析现有的上游服务配置
    
    参数:
        upstream_content: upstream块内容
        
    返回:
        dict: 现有配置信息
    """
    settings = {
        'servers': [],
        'load_balancing': {},
        'timeout_settings': {},
        'retry_mechanism': {},
        'health_check': {},
        'other_configs': {}
    }
    
    try:
        # 解析服务器配置
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = re.finditer(server_pattern, upstream_content)  # NOSONAR
        
        for match in server_matches:
            server_config = match.group(1).strip()
            settings['servers'].append(server_config)
        
        # 解析负载均衡策略
        lb_methods = ['ip_hash', 'least_conn', 'hash', 'sticky']
        for method in lb_methods:
            if re.search(rf'\b{method}\b', upstream_content):  # NOSONAR
                settings['load_balancing']['method'] = method
                if method == 'hash':
                    hash_match = re.search(r'hash\s+([^;]+);', upstream_content)  # NOSONAR
                    if hash_match:
                        settings['load_balancing']['hash_key'] = hash_match.group(1).strip()
        
        # 解析超时设置
        timeout_patterns = {
            'proxy_connect_timeout': r'proxy_connect_timeout\s+([^;]+);',
            'proxy_send_timeout': r'proxy_send_timeout\s+([^;]+);',
            'proxy_read_timeout': r'proxy_read_timeout\s+([^;]+);',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);'
        }
        
        for key, pattern in timeout_patterns.items():
            match = re.search(pattern, upstream_content)  # NOSONAR
            if match:
                settings['timeout_settings'][key] = match.group(1).strip()
        
        # 解析重试机制
        retry_patterns = {
            'proxy_next_upstream': r'proxy_next_upstream\s+([^;]+);',
            'proxy_next_upstream_timeout': r'proxy_next_upstream_timeout\s+([^;]+);',
            'proxy_next_upstream_tries': r'proxy_next_upstream_tries\s+([^;]+);'
        }
        
        for key, pattern in retry_patterns.items():
            match = re.search(pattern, upstream_content)  # NOSONAR
            if match:
                settings['retry_mechanism'][key] = match.group(1).strip()
        
        # 解析熔断阈值（服务器级别的）
        for server_config in settings['servers']:
            if 'max_fails=' in server_config:
                max_fails_match = re.search(r'max_fails=(\d+)', server_config)  # NOSONAR
                if max_fails_match:
                    settings['other_configs']['max_fails'] = max_fails_match.group(1)
            if 'fail_timeout=' in server_config:
                fail_timeout_match = re.search(r'fail_timeout=([^\s]+)', server_config)  # NOSONAR
                if fail_timeout_match:
                    settings['other_configs']['fail_timeout'] = fail_timeout_match.group(1)
        
    except Exception as e:
        logger.error(f"解析现有上游服务配置失败: {e}")
    
    return settings

def produce_upstream_config(
    upstream_name: str,
    servers: List[str],
    load_balancing_method: Optional[str] = None,
    hash_key: Optional[str] = None,
    timeout_settings: Optional[Dict[str, str]] = None,
    retry_settings: Optional[Dict[str, str]] = None,
    fail_thresholds: Optional[Dict[str, str]] = None,
    existing_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    生成上游服务配置
    
    参数:
        upstream_name: 上游服务名称
        servers: 服务器列表
        load_balancing_method: 负载均衡方法
        hash_key: 哈希键（仅用于hash方法）
        timeout_settings: 超时设置
        retry_settings: 重试设置
        fail_thresholds: 熔断阈值设置
        existing_config: 现有配置信息
        
    返回:
        str: 生成的配置内容
    """
    try:
        lines = [f"upstream {upstream_name} {{"]
        
        # 添加负载均衡策略
        if load_balancing_method:
            if load_balancing_method == 'ip_hash':
                lines.append("    ip_hash;")
            elif load_balancing_method == 'least_conn':
                lines.append("    least_conn;")
            elif load_balancing_method == 'hash' and hash_key:
                lines.append(f"    hash {hash_key};")
            elif load_balancing_method == 'sticky':
                lines.append("    sticky;")
        
        # 添加服务器配置（包含熔断阈值）
        for server in servers:
            server_line = f"    server {server}"
            
            # 添加熔断阈值设置
            if fail_thresholds:
                if 'max_fails' in fail_thresholds:
                    server_line += f" max_fails={fail_thresholds['max_fails']}"
                if 'fail_timeout' in fail_thresholds:
                    server_line += f" fail_timeout={fail_thresholds['fail_timeout']}"
            
            server_line += ";"
            lines.append(server_line)
        
        # 添加超时设置
        if timeout_settings:
            for key, value in timeout_settings.items():
                if key == 'connect_timeout':
                    lines.append(f"    proxy_connect_timeout {value};")
                elif key == 'send_timeout':
                    lines.append(f"    proxy_send_timeout {value};")
                elif key == 'read_timeout':
                    lines.append(f"    proxy_read_timeout {value};")
                elif key == 'keepalive_timeout':
                    lines.append(f"    keepalive_timeout {value};")
        
        # 添加重试设置
        if retry_settings:
            for key, value in retry_settings.items():
                if key == 'next_upstream':
                    lines.append(f"    proxy_next_upstream {value};")
                elif key == 'next_upstream_timeout':
                    lines.append(f"    proxy_next_upstream_timeout {value};")
                elif key == 'next_upstream_tries':
                    lines.append(f"    proxy_next_upstream_tries {value};")
        
        # 保留现有配置中的其他设置
        if existing_config:
            # 保留健康检查配置
            if existing_config.get('health_check'):
                health_check = existing_config['health_check']
                if health_check.get('enabled', False):
                    lines.append("    health_check;")
                    for key, value in health_check.items():
                        if key != 'enabled' and value:
                            lines.append(f"    health_check_{key} {value};")
            
            # 保留其他配置
            if 'other_configs' in existing_config:
                for key, value in existing_config['other_configs'].items():
                    if key not in ['max_fails', 'fail_timeout']:  # 这些已经在服务器配置中处理
                        lines.append(f"    {key} {value};")
        
        lines.append("}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"生成上游服务配置失败: {e}")
        return ""

def save_config_file(cfg_filepath: str) -> Optional[str]:
    """
    备份配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 备份文件路径，如果失败返回None
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{cfg_filepath}.backup_{timestamp}"
        shutil.copy2(cfg_filepath, backup_path)
        logger.info(f"配置文件已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份配置文件失败: {e}")
        return None

def certify_nginx_config(config_content: str) -> Tuple[bool, str]:
    """
    验证Nginx配置语法
    
    参数:
        config_content: 配置内容
        
    返回:
        tuple: (是否有效, 错误信息)
    """
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp_file:
            temp_file.write(config_content)
            temp_file.flush()
            temp_path = temp_file.name
        
        # 验证配置语法
        output = subprocess.run(['nginx', '-t', '-c', temp_path], capture_output=True, text=True)
        
        # 删除临时文件
        os.unlink(temp_path)
        
        if output.returncode == 0:
            return True, "配置语法正确"
        else:
            err_text = output.stderr if output.stderr else output.stdout
            return False, err_text
            
    except Exception as e:
        logger.error(f"验证Nginx配置失败: {e}")
        return False, str(e)

def reload_nginx() -> Tuple[bool, str]:
    """
    重新加载Nginx配置
    
    返回:
        tuple: (是否成功, 错误信息)
    """
    try:
        # 尝试平滑重载
        output = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)
        
        if output.returncode == 0:
            return True, "Nginx配置重载成功"
        else:
            err_text = output.stderr if output.stderr else output.stdout
            return False, err_text
            
    except Exception as e:
        logger.error(f"重载Nginx配置失败: {e}")
        return False, str(e)