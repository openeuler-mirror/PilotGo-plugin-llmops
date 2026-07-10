#!/usr/bin/env python3
"""
Nginx自定义日志格式设置工具
支持设置/新增自定义日志格式（如添加IP/UA/响应时间字段）
"""

import os
import re
import subprocess
import logging
import shutil
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_format')

# 预定义的日志格式变量
PREDEFINED_VARIABLES = {
    # 客户端信息
    'remote_addr': '客户端IP地址',
    'remote_user': '客户端用户名',
    'time_local': '本地时间',
    'request': '请求行',
    'status': '响应状态码',
    'body_bytes_sent': '响应体字节数',
    'http_referer': '来源页面',
    'http_user_agent': '用户代理',
    'http_x_forwarded_for': '代理服务器IP',
    
    # 连接信息
    'connection': '连接序列号',
    'connection_requests': '当前连接请求数',
    'request_time': '请求处理时间',
    'upstream_response_time': '上游服务器响应时间',
    'upstream_connect_time': '上游服务器连接时间',
    'upstream_header_time': '上游服务器头时间',
    
    # 服务器信息
    'server_name': '服务器名称',
    'server_addr': '服务器地址',
    'server_port': '服务器端口',
    'host': '请求的主机名',
    
    # 请求信息
    'request_method': '请求方法',
    'request_uri': '请求URI',
    'request_length': '请求长度',
    'request_id': '请求ID',
    
    # 缓存信息
    'upstream_cache_status': '上游缓存状态',
    'sent_http_content_type': '响应内容类型',
    'sent_http_content_length': '响应内容长度',
    
    # SSL信息
    'ssl_protocol': 'SSL协议版本',
    'ssl_cipher': 'SSL加密算法',
    'ssl_session_reused': 'SSL会话重用',
    
    # 地理位置信息
    'geoip_country_code': '国家代码',
    'geoip_country_name': '国家名称',
    'geoip_city': '城市',
    'geoip_region': '区域'
}

# 预定义的日志格式模板
PREDEFINED_FORMATS = {
    'main': '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"',
    'combined': '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for"',
    'extended': '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" $request_time $upstream_response_time',
    'detailed': '$remote_addr - $remote_user [$time_local] "$request_method $request_uri HTTP/$server_protocol" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_time $upstream_response_time $upstream_cache_status',
    'security': '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_time $ssl_protocol $ssl_cipher',
    'performance': '$remote_addr [$time_local] "$request" $status $body_bytes_sent $request_time $upstream_response_time $upstream_connect_time $upstream_header_time'
}

def verify_nginx_installation() -> bool:
    """
    检查Nginx是否已安装
    
    返回:
        bool: Nginx是否已安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx主配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
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

def save_config_file(cfg_filepath: str) -> str:
    """
    备份配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 备份文件路径
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"save_config_file: cfg_filepath 路径验证失败：{err_text}")
            raise ValueError(f"配置文件路径不安全：{err_text}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{cfg_filepath}.backup.{timestamp}"
        shutil.copy2(cfg_filepath, backup_path)
        logger.info(f"配置文件已备份到：{backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份配置文件失败: {e}")
        raise

def fetch_current_log_formats(cfg_filepath: str) -> Dict[str, Any]:
    """
    获取当前自定义日志格式配置
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 当前日志格式配置信息
    """
    current_formats = {
        'formats': [],
        'source_file': cfg_filepath
    }
    
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_current_log_formats: cfg_filepath 路径验证失败：{err_text}")
            return current_formats
        
        if not os.path.exists(cfg_filepath):
            return current_formats
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析log_format指令
        format_pattern = r'log_format\s+([^{]+)\{([^}]+)\}'  # NOSONAR
        format_matches = re.finditer(format_pattern, body, re.DOTALL)  # NOSONAR
        
        for match in format_matches:
            format_name = match.group(1).strip()
            format_content = match.group(2).strip()
            
            # 提取变量
            variables = re.findall(r'\$(\w+)', format_content)  # NOSONAR
            
            current_formats['formats'].append({
                'name': format_name,
                'format': format_content,
                'variables': sorted(set(variables)),
                'line_number': body[:match.start()].count('\n') + 1
            })
        
        # 检查include文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        
        for include in includes:
            include_path = include.strip().strip('"\'')
            if not os.path.isabs(include_path):
                include_path = os.path.join(os.path.dirname(cfg_filepath), include_path)
            
            if os.path.exists(include_path):
                include_formats = fetch_current_log_formats(include_path)
                current_formats['formats'].extend(include_formats['formats'])
        
    except Exception as e:
        logger.error(f"获取当前日志格式配置失败: {e}")
    
    return current_formats

def certify_log_format(format_name: str, format_content: str) -> Tuple[bool, str]:
    """
    验证日志格式
    
    参数:
        format_name: 格式名称
        format_content: 格式内容
        
    返回:
        tuple: (是否有效, 错误信息)
    """
    try:
        # 验证格式名称
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', format_name):  # NOSONAR
            return False, "格式名称只能包含字母、数字和下划线，且不能以数字开头"
        
        # 验证格式内容
        if not format_content.strip():
            return False, "格式内容不能为空"
        
        # 检查变量格式
        variables = re.findall(r'\$(\w+)', format_content)  # NOSONAR
        for var in variables:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var):  # NOSONAR
                return False, f"变量格式不正确: ${var}"
        
        # 检查引号匹配
        quote_count = format_content.count('"')
        if quote_count % 2 != 0:
            return False, "引号不匹配"
        
        return True, "格式验证通过"
        
    except Exception as e:
        logger.error(f"验证日志格式失败: {e}")
        return False, f"验证失败: {e}"

def add_log_format_to_config(cfg_filepath: str, format_name: str, 
                           format_content: str, target_file: str = None) -> Tuple[bool, str]:
    """
    添加日志格式到配置文件
    
    参数:
        cfg_filepath: 主配置文件路径
        format_name: 格式名称
        format_content: 格式内容
        target_file: 目标配置文件路径
        
    返回:
        tuple: (是否成功，修改后的内容)
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"add_log_format_to_config: cfg_filepath 路径验证失败：{err_text}")
            return False, f"配置文件路径不安全：{err_text}"
        
        # 安全验证：验证 format_name 标识符参数
        valid, err_text = validate_identifier_param(format_name)
        if not valid:
            logger.error(f"add_log_format_to_config: format_name 验证失败：{err_text}")
            return False, f"格式名称不安全：{err_text}"
        
        target_file = cfg_filepath if target_file is None else target_file
        # 安全验证：验证 target_file 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(target_file, allow_absolute=True)
        if not valid:
            logger.error(f"add_log_format_to_config: target_file 路径验证失败：{err_text}")
            return False, f"目标文件路径不安全：{err_text}"
        
        if not os.path.exists(target_file):
            # 如果目标文件不存在，创建它
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write('# Nginx 日志格式配置\n\n')
        
        with open(target_file, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 检查是否已存在同名格式
        existing_pattern = rf'log_format\s+{format_name}\s*{{[^}}]+}}'  # NOSONAR
        if re.search(existing_pattern, body, re.DOTALL):  # NOSONAR
            return False, f"格式名称 '{format_name}' 已存在"
        
        # 在http块内添加log_format指令
        http_pattern = r'(http\s*\{)'  # NOSONAR
        http_match = re.search(http_pattern, body)  # NOSONAR
        
        if http_match:
            # 在http块开头添加
            insert_pos = http_match.end()
            log_format_line = f'\n    log_format {format_name} {{{format_content}}};\n'
            new_content = body[:insert_pos] + log_format_line + body[insert_pos:]
        else:
            # 如果没有http块，在文件末尾添加
            log_format_line = f'\nhttp {{\n    log_format {format_name} {{{format_content}}};\n}}\n'
            new_content = body + log_format_line
        
        return True, new_content
        
    except Exception as e:
        logger.error(f"添加日志格式到配置文件失败: {e}")
        return False, f"添加失败: {e}"

def modify_existing_log_format(cfg_filepath: str, format_name: str, 
                              new_format_content: str) -> Tuple[bool, str]:
    """
    修改现有的日志格式
    
    参数:
        cfg_filepath: 配置文件路径
        format_name: 格式名称
        new_format_content: 新的格式内容
        
    返回:
        tuple: (是否成功，消息)
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"modify_existing_log_format: cfg_filepath 路径验证失败：{err_text}")
            return False, f"配置文件路径不安全：{err_text}"
        
        # 安全验证：验证 format_name 标识符参数
        valid, err_text = validate_identifier_param(format_name)
        if not valid:
            logger.error(f"modify_existing_log_format: format_name 验证失败：{err_text}")
            return False, f"格式名称不安全：{err_text}"
        
        if not os.path.exists(cfg_filepath):
            return False, f"配置文件不存在：{cfg_filepath}"
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 查找并替换现有的log_format
        pattern = rf'(log_format\s+{format_name}\s*{{)[^}}]+(}})'  # NOSONAR
        replacement = rf'\1{new_format_content}\2'
        
        new_content = re.sub(pattern, replacement, body, flags=re.DOTALL)  # NOSONAR
        
        if new_content == body:
            return False, f"未找到格式 '{format_name}'"
        
        return True, new_content
        
    except Exception as e:
        logger.error(f"修改现有日志格式失败: {e}")
        return False, f"修改失败: {e}"

def remove_log_format(cfg_filepath: str, format_name: str) -> Tuple[bool, str]:
    """
    删除指定的日志格式
    
    参数:
        cfg_filepath: 配置文件路径
        format_name: 格式名称
        
    返回:
        tuple: (是否成功，消息)
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, err_text = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"remove_log_format: cfg_filepath 路径验证失败：{err_text}")
            return False, f"配置文件路径不安全：{err_text}"
        
        # 安全验证：验证 format_name 标识符参数
        valid, err_text = validate_identifier_param(format_name)
        if not valid:
            logger.error(f"remove_log_format: format_name 验证失败：{err_text}")
            return False, f"格式名称不安全：{err_text}"
        
        if not os.path.exists(cfg_filepath):
            return False, f"配置文件不存在：{cfg_filepath}"
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 查找并删除log_format指令
        pattern = rf'log_format\s+{format_name}\s*{{[^}}]+}};\s*\n?'  # NOSONAR
        
        new_content = re.sub(pattern, '', body, flags=re.DOTALL)  # NOSONAR
        
        if new_content == body:
            return False, f"未找到格式 '{format_name}'"
        
        return True, new_content
        
    except Exception as e:
        logger.error(f"删除日志格式失败: {e}")
        return False, f"删除失败: {e}"