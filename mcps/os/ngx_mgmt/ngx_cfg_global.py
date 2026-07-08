#!/usr/bin/env python3

from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import re
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

# 导入工具函数
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_global')

# 常见的Nginx全局配置项
GLOBAL_DIRECTIVES = {
    # 核心配置
    'user': '指定运行Nginx工作进程的用户和用户组',
    'worker_processes': '指定Nginx要开启的工作进程数量',
    'worker_cpu_affinity': '绑定工作进程到指定CPU核心',
    'worker_priority': '设置工作进程的优先级',
    'worker_rlimit_nofile': '设置工作进程可以打开的最大文件描述符数量',
    'worker_rlimit_core': '设置工作进程可以使用的核心文件大小限制',
    'working_directory': '指定工作进程的工作目录',

    # 错误日志配置
    'error_log': '指定错误日志的位置和级别',

    # PID文件配置
    'pid': '指定存储Nginx主进程PID的文件路径',

    # 事件模块配置
    'events': {
        'worker_connections': '每个工作进程可以同时处理的最大连接数',
        'use': '指定使用的事件驱动模型',
        'multi_accept': '是否允许工作进程一次接受多个连接',
        'accept_mutex': '是否启用accept互斥锁',
        'accept_mutex_delay': 'accept互斥锁的超时时间',
        'debug_connection': '指定调试连接的IP地址'
    },

    # HTTP模块配置
    'http': {
        'include': '包含其他配置文件',
        'default_type': '默认MIME类型',
        'sendfile': '是否使用sendfile系统调用',
        'tcp_nopush': '是否启用tcp_nopush选项',
        'tcp_nodelay': '是否启用tcp_nodelay选项',
        'keepalive_timeout': '保持连接的超时时间',
        'keepalive_requests': '单个连接可以处理的最大请求数',
        'client_header_timeout': '读取客户端请求头的超时时间',
        'client_body_timeout': '读取客户端请求体的超时时间',
        'send_timeout': '向客户端发送响应的超时时间',
        'server_tokens': '是否在错误页面和响应头中显示Nginx版本信息',
        'server_names_hash_bucket_size': '服务器名称哈希表的大小',
        'server_names_hash_max_size': '服务器名称哈希表的最大大小',
        'types_hash_max_size': 'MIME类型哈希表的最大大小',
        'types_hash_bucket_size': 'MIME类型哈希表的大小',
        'variables_hash_max_size': '变量哈希表的最大大小',
        'variables_hash_bucket_size': '变量哈希表的大小',
        'client_max_body_size': '客户端请求体的最大允许大小',
        'client_body_buffer_size': '客户端请求体的缓冲区大小',
        'client_header_buffer_size': '客户端请求头的缓冲区大小',
        'large_client_header_buffers': '处理大型请求头的缓冲区数量和大小',
        'client_body_temp_path': '客户端请求体临时文件的存储路径',
        'fastcgi_temp_path': 'FastCGI临时文件的存储路径',
        'uwsgi_temp_path': 'uWSGI临时文件的存储路径',
        'scgi_temp_path': 'SCGI临时文件的存储路径',
        'proxy_temp_path': '代理临时文件的存储路径',
        'ignore_invalid_headers': '是否忽略无效的请求头',
        'underscores_in_headers': '是否允许请求头中包含下划线',
        'merge_slashes': '是否合并请求URI中的多个斜杠'
    }
}

def analyze_nginx_config(config_file: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件，提取全局配置项

    参数:
        config_file: Nginx配置文件路径

    返回:
        包含所有全局配置项的字典
    """
    try:
        if not os.path.exists(config_file):
            return {'error': f'配置文件不存在: {config_file}'}

        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 初始化结果字典
        global_config = {
            'config_file': config_file,
            'global_directives': {},
            'events_directives': {},
            'http_directives': {},
            'includes': [],
            'parsing_errors': []
        }

        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR

        # 解析全局指令（不在任何块内的指令）
        global_pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*?);'  # NOSONAR
        global_matches = re.findall(global_pattern, body, re.MULTILINE)  # NOSONAR

        for directive, value in global_matches:
            # 过滤掉块指令
            if directive not in ['events', 'http', 'server', 'location', 'upstream', 'mail']:
                global_config['global_directives'][directive] = value.strip()

        # 解析events块
        events_pattern = r'events\s*{(.*?)}'  # NOSONAR
        events_match = re.search(events_pattern, body, re.DOTALL)  # NOSONAR
        if events_match:
            events_content = events_match.group(1)
            events_directives = re.findall(global_pattern, events_content, re.MULTILINE)  # NOSONAR
            for directive, value in events_directives:
                global_config['events_directives'][directive] = value.strip()

        # 解析http块
        http_pattern = r'http\s*{(.*?)(?=\s*}\s*$)'  # NOSONAR
        http_match = re.search(http_pattern, body, re.DOTALL)  # NOSONAR
        if http_match:
            http_content = http_match.group(1)
            # 提取http块内的全局指令（不包括嵌套块）
            http_directives = re.findall(global_pattern, http_content, re.MULTILINE)  # NOSONAR
            for directive, value in http_directives:
                # 过滤掉嵌套块指令
                if directive not in ['server', 'location', 'upstream', 'map', 'geo', 'split_clients', 'perl', 'limit_conn_zone', 'limit_req_zone']:
                    global_config['http_directives'][directive] = value.strip()

        # 解析include指令
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        include_matches = re.findall(include_pattern, body)  # NOSONAR
        for include_path in include_matches:
            global_config['includes'].append(include_path.strip())

        return global_config

    except Exception as e:
        logger.error(f'解析Nginx配置文件失败: {e}')
        return {
            'error': f'解析配置文件失败: {e}',
            'config_file': config_file
        }