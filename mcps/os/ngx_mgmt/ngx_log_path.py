import glob
import logging
import os
import platform
import re
import subprocess

from .utils import (

    check_nginx_installation, get_basic_paths, get_system_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_path')

def fetch_nginx_log_path():
    """
    获取Nginx访问日志和错误日志的存储路径、文件名称、日志格式的MCP工具

    返回:
        格式化的Nginx日志路径信息字符串，包含：
        - 访问日志路径和格式
        - 错误日志路径和格式
        - 日志轮转配置
        - 日志文件状态
        - 自定义日志格式定义
    """
    try:
        output = []
        output.append('=== Nginx日志路径和格式信息 ===')

        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('=============================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")

        # 获取主配置文件路径
        cfg_state = fetch_nginx_config_info()
        if cfg_state['config_file'] == 'Unknown':
            output.append(f"错误: 无法找到Nginx配置文件")
            output.append('=============================')
            return '\n'.join(output)

        output.append(f"主配置文件: {cfg_state['config_file']}")

        # 解析配置文件获取日志信息
        log_info = analyze_nginx_log_config(cfg_state['config_file'])

        # 显示访问日志信息
        output.append(f"\n=== 访问日志信息 ===")
        if log_info['access_logs']:
            for i, access_log in enumerate(log_info['access_logs'], 1):
                output.append(f"访问日志 {i}:")
                output.append(f"  路径: {access_log['path']}")
                output.append(f"  格式: {access_log['format']}")
                output.append(f"  缓冲区: {access_log['buffer']}")
                output.append(f"  刷新: {access_log['flush']}")
                output.append(f"  压缩: {access_log['gzip']}")
                output.append(f"  文件状态: {access_log['state']}")
                if access_log['size'] != 'Unknown':
                    output.append(f"  文件大小: {access_log['size']}")
        else:
            output.append("未找到访问日志配置")

        # 显示错误日志信息
        output.append(f"\n=== 错误日志信息 ===")
        if log_info['error_logs']:
            for i, error_log in enumerate(log_info['error_logs'], 1):
                output.append(f"错误日志 {i}:")
                output.append(f"  路径: {error_log['path']}")
                output.append(f"  级别: {error_log['level']}")
                output.append(f"  文件状态: {error_log['state']}")
                if error_log['size'] != 'Unknown':
                    output.append(f"  文件大小: {error_log['size']}")
        else:
            output.append("未找到错误日志配置")

        # 显示日志格式定义
        output.append(f"\n=== 日志格式定义 ===")
        if log_info['log_formats']:
            for format_name, format_string in log_info['log_formats'].items():
                output.append(f"格式 '{format_name}': {format_string}")
        else:
            output.append("未找到自定义日志格式定义")

        # 显示日志轮转配置
        output.append(f"\n=== 日志轮转配置 ===")
        if log_info['logrotate_config']:
            for config_item in log_info['logrotate_config']:
                output.append(config_item)
        else:
            output.append("未找到日志轮转配置")

        # 显示日志目录权限
        output.append(f"\n=== 日志目录权限 ===")
        for perm_info in log_info['directory_permissions']:
            output.append(perm_info)

        output.append('\n=============================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx日志路径信息失败: {e}')
        return f'获取Nginx日志路径信息失败: {e}'