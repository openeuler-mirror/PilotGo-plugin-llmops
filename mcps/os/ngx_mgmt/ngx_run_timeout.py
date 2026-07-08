from datetime import datetime
import logging
import os
import re
import subprocess

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_timeout')

def fetch_nginx_runtime_timeout():
    """
    获取Nginx的各种超时配置，包括：
    - 请求超时时间
    - 连接超时时间
    - 发送超时时间
    - 接收超时时间
    - 客户端保持连接超时时间
    """
    try:
        output = []
        output.append('=== Nginx超时配置信息 ===')

        # 获取nginx进程信息
        proc_info = get_nginx_process_info()
        if proc_info['status'] == '已停止':
            output.append('Nginx服务未运行')
            return '\n'.join(output)

        # 获取nginx配置文件路径
        cfg_filepath = get_nginx_config_path()
        if not cfg_filepath:
            output.append('无法获取Nginx配置文件路径')
            return '\n'.join(output)

        # 解析配置文件获取超时设置
        timeout_configs = analyze_timeout_configs(cfg_filepath)

        # 显示各种超时配置
        output.append('\n=== 请求超时配置 ===')
        output.append(f"client_body_timeout: {timeout_configs.get('client_body_timeout', '未设置 (默认60秒)')}")
        output.append(f"client_header_timeout: {timeout_configs.get('client_header_timeout', '未设置 (默认60秒)')}")
        output.append(f"keepalive_timeout: {timeout_configs.get('keepalive_timeout', '未设置 (默认75秒)')}")
        output.append(f"send_timeout: {timeout_configs.get('send_timeout', '未设置 (默认60秒)')}")

        output.append('\n=== 连接超时配置 ===')
        output.append(f"client_body_buffer_size: {timeout_configs.get('client_body_buffer_size', '未设置 (默认16k)')}")
        output.append(f"client_header_buffer_size: {timeout_configs.get('client_header_buffer_size', '未设置 (默认1k)')}")
        output.append(f"large_client_header_buffers: {timeout_configs.get('large_client_header_buffers', '未设置 (默认4 8k)')}")
        output.append(f"client_max_body_size: {timeout_configs.get('client_max_body_size', '未设置 (默认1m)')}")

        output.append('\n=== 代理超时配置 ===')
        output.append(f"proxy_connect_timeout: {timeout_configs.get('proxy_connect_timeout', '未设置 (默认60秒)')}")
        output.append(f"proxy_send_timeout: {timeout_configs.get('proxy_send_timeout', '未设置 (默认60秒)')}")
        output.append(f"proxy_read_timeout: {timeout_configs.get('proxy_read_timeout', '未设置 (默认60秒)')}")

        output.append('\n=== FastCGI超时配置 ===')
        output.append(f"fastcgi_connect_timeout: {timeout_configs.get('fastcgi_connect_timeout', '未设置 (默认60秒)')}")
        output.append(f"fastcgi_send_timeout: {timeout_configs.get('fastcgi_send_timeout', '未设置 (默认60秒)')}")
        output.append(f"fastcgi_read_timeout: {timeout_configs.get('fastcgi_read_timeout', '未设置 (默认60秒)')}")

        output.append('\n=== uWSGI超时配置 ===')
        output.append(f"uwsgi_connect_timeout: {timeout_configs.get('uwsgi_connect_timeout', '未设置 (默认60秒)')}")
        output.append(f"uwsgi_send_timeout: {timeout_configs.get('uwsgi_send_timeout', '未设置 (默认60秒)')}")
        output.append(f"uwsgi_read_timeout: {timeout_configs.get('uwsgi_read_timeout', '未设置 (默认60秒)')}")

        output.append('\n=== SCGI超时配置 ===')
        output.append(f"scgi_connect_timeout: {timeout_configs.get('scgi_connect_timeout', '未设置 (默认60秒)')}")
        output.append(f"scgi_send_timeout: {timeout_configs.get('scgi_send_timeout', '未设置 (默认60秒)')}")
        output.append(f"scgi_read_timeout: {timeout_configs.get('scgi_read_timeout', '未设置 (默认60秒)')}")

        output.append('\n=== 其他超时配置 ===')
        output.append(f"resolver_timeout: {timeout_configs.get('resolver_timeout', '未设置 (默认30秒)')}")
        output.append(f" lingering_time: {timeout_configs.get('lingering_time', '未设置 (默认30秒)')}")
        output.append(f" lingering_timeout: {timeout_configs.get('lingering_timeout', '未设置 (默认5秒)')}")

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx超时配置失败: {e}')
        return f'获取Nginx超时配置失败: {e}'