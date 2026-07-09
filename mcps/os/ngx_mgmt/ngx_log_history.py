from datetime import datetime, timedelta
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
logger = logging.getLogger('nginx_log_history')

def fetch_nginx_log_history(start_time=None, end_time=None, ip_address=None, url_pattern=None, status_code=None, log_type='access', max_lines=1000):
    """
    获取指定时间范围的历史日志，支持按时间/IP/URL/状态码过滤的MCP工具

    参数:
        start_time: 开始时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)
        end_time: 结束时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)
        ip_address: IP地址过滤 (支持部分匹配)
        url_pattern: URL模式过滤 (支持正则表达式)
        status_code: 状态码过滤 (如: 200, 404, 500)
        log_type: 日志类型 ('access', 'error')
        max_lines: 最大返回行数

    返回:
        格式化的历史日志信息字符串
    """
    try:
        output = []
        output.append('=== Nginx历史日志查询 ===')

        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('============================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")
        output.append(f"日志类型: {log_type}")
        output.append(f"最大行数: {max_lines}")

        # 显示过滤条件
        output.append(f"\n=== 过滤条件 ===")
        if start_time:
            output.append(f"开始时间: {start_time}")
        if end_time:
            output.append(f"结束时间: {end_time}")
        if ip_address:
            output.append(f"IP地址: {ip_address}")
        if url_pattern:
            output.append(f"URL模式: {url_pattern}")
        if status_code:
            output.append(f"状态码: {status_code}")

        # 获取日志文件列表
        log_files = fetch_nginx_log_files(log_type, include_rotated=True)
        if not log_files:
            output.append(f"错误: 未找到{log_type}日志文件")
            output.append('============================')
            return '\n'.join(output)

        output.append(f"\n=== 日志文件列表 ===")
        for log_file in log_files:
            output.append(f"文件: {log_file['path']}")
            output.append(f"类型: {log_file['type']}")
            output.append(f"大小: {log_file['size']}")
            output.append(f"修改时间: {log_file['mtime']}")
            output.append(f"时间范围: {log_file['time_range']}")

        # 解析时间范围
        start_dt, end_dt = analyze_time_range(start_time, end_time)

        # 查询日志内容
        output.append(f"\n=== 查询结果 ===")
        log_content = query_log_content(log_files, start_dt, end_dt, ip_address, url_pattern, status_code, max_lines)

        if log_content:
            output.extend(log_content)
            output.append(f"\n总计找到 {len(log_content)} 条匹配记录")
        else:
            output.append("未找到匹配的日志记录")
            output.append("建议: 调整过滤条件或检查时间范围")

        # 显示统计信息
        if log_content:
            output.append(f"\n=== 统计信息 ===")
            stats = produce_statistics(log_content, log_type)
            output.extend(stats)

        output.append('\n============================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'查询Nginx历史日志失败: {e}')
        return f'查询Nginx历史日志失败: {e}'

def fetch_nginx_log_files(log_type, include_rotated=True):
    """
    获取Nginx日志文件列表，包括轮转文件

    参数:
        log_type: 日志类型
        include_rotated: 是否包含轮转文件

    返回:
        list: 日志文件信息列表
    """
    try:
        log_files = []

        # 获取主日志文件
        main_files = fetch_main_log_files(log_type)
        log_files.extend(main_files)

        # 获取轮转日志文件
        if include_rotated:
            rotated_files = fetch_rotated_log_files(log_type)
            log_files.extend(rotated_files)

        # 按修改时间排序（最新的在前）
        log_files.sort(key=lambda x: x.get('mtime_timestamp', 0), reverse=True)

        return log_files

    except Exception as e:
        logger.error(f'获取Nginx日志文件列表失败: {e}')
        return []

def fetch_main_log_files(log_type):
    """
    获取主日志文件

    参数:
        log_type: 日志类型

    返回:
        list: 主日志文件列表
    """
    try:
        log_files = []
        common_log_dirs = ['/var/log/nginx', '/usr/local/nginx/logs', '/var/log']

        for log_dir in common_log_dirs:
            if os.path.exists(log_dir):
                # 访问日志文件
                if log_type == 'access':
                    access_logs = [
                        os.path.join(log_dir, 'access.log'),
                        os.path.join(log_dir, 'access_log'),
                        os.path.join(log_dir, 'nginx-access.log')
                    ]
                    for log_path in access_logs:
                        if os.path.exists(log_path):
                            file_info = fetch_log_file_info(log_path, 'access')
                            if file_info:
                                log_files.append(file_info)
                            break

                # 错误日志文件
                elif log_type == 'error':
                    error_logs = [
                        os.path.join(log_dir, 'error.log'),
                        os.path.join(log_dir, 'error_log'),
                        os.path.join(log_dir, 'nginx-error.log')
                    ]
                    for log_path in error_logs:
                        if os.path.exists(log_path):
                            file_info = fetch_log_file_info(log_path, 'error')
                            if file_info:
                                log_files.append(file_info)
                            break

        return log_files

    except Exception as e:
        logger.error(f'获取主日志文件失败: {e}')
        return []

def fetch_rotated_log_files(log_type):
    """
    获取轮转的日志文件

    参数:
        log_type: 日志类型

    返回:
        list: 轮转日志文件列表
    """
    try:
        rotated_files = []
        common_log_dirs = ['/var/log/nginx', '/usr/local/nginx/logs', '/var/log']

        for log_dir in common_log_dirs:
            if os.path.exists(log_dir):
                # 查找轮转的访问日志文件
                if log_type == 'access':
                    patterns = [
                        os.path.join(log_dir, 'access.log.*'),
                        os.path.join(log_dir, 'access.log.*.gz'),
                        os.path.join(log_dir, 'access_log.*'),
                        os.path.join(log_dir, 'nginx-access.log.*')
                    ]

                # 查找轮转的错误日志文件
                elif log_type == 'error':
                    patterns = [
                        os.path.join(log_dir, 'error.log.*'),
                        os.path.join(log_dir, 'error.log.*.gz'),
                        os.path.join(log_dir, 'error_log.*'),
                        os.path.join(log_dir, 'nginx-error.log.*')
                    ]

                for pattern in patterns:
                    for log_path in glob.glob(pattern):
                        file_info = fetch_log_file_info(log_path, log_type)
                        if file_info:
                            rotated_files.append(file_info)

        return rotated_files

    except Exception as e:
        logger.error(f'获取轮转日志文件失败: {e}')
        return []

def fetch_log_file_info(log_path, log_type):
    """
    获取日志文件详细信息

    参数:
        log_path: 文件路径
        log_type: 日志类型

    返回:
        dict: 文件信息字典
    """
    try:
        if not os.path.exists(log_path):
            return None

        stat_info = os.stat(log_path)
        mtime = datetime.fromtimestamp(stat_info.st_mtime)

        # 估算文件时间范围（基于文件名和修改时间）
        time_range = estimate_file_time_range(log_path, mtime)

        return {
            'path': log_path,
            'type': log_type,
            'size': render_file_size(stat_info.st_size),
            'mtime': mtime.strftime('%Y-%m-%d %H:%M:%S'),
            'mtime_timestamp': stat_info.st_mtime,
            'time_range': time_range
        }

    except Exception as e:
        logger.error(f'获取日志文件信息失败: {e}')
        return None