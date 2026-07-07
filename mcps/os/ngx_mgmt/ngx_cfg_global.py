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

def fetch_global_config() -> Dict[str, Any]:
    """
    获取Nginx全局配置项

    返回:
        包含所有全局配置项及其说明的字典
    """
    try:
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            return {
                'error': 'Nginx未安装',
                'suggestion': nginx_status.get('suggestion', '请安装Nginx')
            }

        # 获取配置文件路径
        cfg_state = get_nginx_config_info()
        config_file = cfg_state.get('config_file', 'Unknown')

        if config_file == 'Unknown':
            return {
                'error': '无法确定Nginx配置文件路径',
                'suggestion': '请检查Nginx安装和配置'
            }

        # 解析配置文件
        parsed_config = analyze_nginx_config(config_file)

        if 'error' in parsed_config:
            return parsed_config

        # 构建结果，包含配置项及其说明
        output = {
            'config_file': config_file,
            'config_test': cfg_state.get('config_test', 'Unknown'),
            'global_directives': {},
            'events_directives': {},
            'http_directives': {},
            'includes': parsed_config.get('includes', []),
            'summary': {
                'total_global_directives': len(parsed_config.get('global_directives', {})),
                'total_events_directives': len(parsed_config.get('events_directives', {})),
                'total_http_directives': len(parsed_config.get('http_directives', {})),
                'total_includes': len(parsed_config.get('includes', []))
            }
        }

        # 添加全局指令及其说明
        for directive, value in parsed_config.get('global_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get(directive, '自定义配置项')
            output['global_directives'][directive] = {
                'value': value,
                'description': description
            }

        # 添加events指令及其说明
        for directive, value in parsed_config.get('events_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get('events', {}).get(directive, '自定义配置项')
            output['events_directives'][directive] = {
                'value': value,
                'description': description
            }

        # 添加http指令及其说明
        for directive, value in parsed_config.get('http_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get('http', {}).get(directive, '自定义配置项')
            output['http_directives'][directive] = {
                'value': value,
                'description': description
            }

        return output

    except Exception as e:
        logger.error(f'获取Nginx全局配置失败: {e}')
        return {
            'error': f'获取全局配置失败: {e}'
        }

def render_global_config_output(config_data: Dict[str, Any]) -> str:
    """
    格式化全局配置输出

    参数:
        config_data: 全局配置数据

    返回:
        格式化后的字符串
    """
    if 'error' in config_data:
        return f"错误: {config_data['error']}\n建议: {config_data.get('suggestion', '')}"

    output = []
    output.append("=" * 60)
    output.append("Nginx全局配置信息")
    output.append("=" * 60)
    output.append(f"配置文件: {config_data['config_file']}")
    output.append(f"配置测试: {config_data['config_test']}")
    output.append("")

    # 全局指令
    if config_data['global_directives']:
        output.append("【全局指令】")
        output.append("-" * 40)
        for directive, info in config_data['global_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【全局指令】")
        output.append("-" * 40)
        output.append("未找到全局指令")
        output.append("")

    # events指令
    if config_data['events_directives']:
        output.append("【Events模块指令】")
        output.append("-" * 40)
        for directive, info in config_data['events_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【Events模块指令】")
        output.append("-" * 40)
        output.append("未找到Events模块指令")
        output.append("")

    # http指令
    if config_data['http_directives']:
        output.append("【HTTP模块指令】")
        output.append("-" * 40)
        for directive, info in config_data['http_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【HTTP模块指令】")
        output.append("-" * 40)
        output.append("未找到HTTP模块指令")
        output.append("")

    # include指令
    if config_data['includes']:
        output.append("【Include指令】")
        output.append("-" * 40)
        for include_path in config_data['includes']:
            output.append(f"include {include_path}")
        output.append("")

    # 统计信息
    summary = config_data['summary']
    output.append("【统计信息】")
    output.append("-" * 40)
    output.append(f"全局指令数量: {summary['total_global_directives']}")
    output.append(f"Events指令数量: {summary['total_events_directives']}")
    output.append(f"HTTP指令数量: {summary['total_http_directives']}")
    output.append(f"Include指令数量: {summary['total_includes']}")

    return "\n".join(output)

TOOL_CONFIG = {
    "name": "fetch_global_config",
    "description": "聚合获取所有全局配置项（如worker_processes、worker_connections）",
    "function": fetch_global_config,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
