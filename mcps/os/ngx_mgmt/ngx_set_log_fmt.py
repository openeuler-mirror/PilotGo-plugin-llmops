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