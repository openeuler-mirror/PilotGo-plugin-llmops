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

def estimate_file_time_range(log_path, mtime):
    """
    估算日志文件的时间范围

    参数:
        log_path: 文件路径
        mtime: 修改时间

    返回:
        str: 时间范围描述
    """
    try:
        filename = os.path.basename(log_path)

        # 检查是否包含日期信息
        date_pattern = r'(\d{4}-\d{2}-\d{2})|(\d{8})|\.(\d+)'  # NOSONAR
        matches = re.findall(date_pattern, filename)  # NOSONAR

        if matches:
            for match in matches:
                date_str = ''.join([g for g in match if g])
                if len(date_str) == 8:  # YYYYMMDD
                    try:
                        file_date = datetime.strptime(date_str, '%Y%m%d')
                        return f"{file_date.strftime('%Y-%m-%d')} (估算)"
                    except Exception:
                        pass
                elif len(date_str) == 10:  # YYYY-MM-DD
                    try:
                        file_date = datetime.strptime(date_str, '%Y-%m-%d')
                        return f"{file_date.strftime('%Y-%m-%d')} (估算)"
                    except Exception:
                        pass

        # 如果没有日期信息，基于修改时间估算
        if 'access.log' in filename or 'error.log' in filename:
            # 主日志文件，包含当前时间
            return f"{mtime.strftime('%Y-%m-%d')} - 当前"
        else:
            # 轮转文件，假设包含一天的数据
            file_date = mtime.date()
            return f"{file_date.strftime('%Y-%m-%d')} (估算)"

    except Exception as e:
        logger.error(f'估算文件时间范围失败: {e}')
        return "时间范围未知"

def analyze_time_range(start_time, end_time):
    """
    解析时间范围

    参数:
        start_time: 开始时间字符串
        end_time: 结束时间字符串

    返回:
        tuple: (start_datetime, end_datetime)
    """
    try:
        now = datetime.now()

        # 解析开始时间
        if start_time:
            if len(start_time) == 10:  # YYYY-MM-DD
                start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            else:  # YYYY-MM-DD HH:MM:SS
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        else:
            # 默认查询最近7天
            start_dt = now - timedelta(days=7)

        # 解析结束时间
        if end_time:
            if len(end_time) == 10:  # YYYY-MM-DD
                end_dt = datetime.strptime(end_time, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
            else:  # YYYY-MM-DD HH:MM:SS
                end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        else:
            end_dt = now

        return start_dt, end_dt

    except Exception as e:
        logger.error(f'解析时间范围失败: {e}')
        # 返回默认时间范围
        now = datetime.now()
        return now - timedelta(days=7), now

def query_log_content(log_files, start_dt, end_dt, ip_address, url_pattern, status_code, max_lines):
    """
    查询日志内容

    参数:
        log_files: 日志文件列表
        start_dt: 开始时间
        end_dt: 结束时间
        ip_address: IP地址过滤
        url_pattern: URL模式过滤
        status_code: 状态码过滤
        max_lines: 最大行数

    返回:
        list: 匹配的日志内容
    """
    try:
        all_matches = []
        processed_files = 0

        for log_file in log_files:
            # 检查文件时间范围是否在查询范围内
            if not is_file_in_time_range(log_file, start_dt, end_dt):
                continue

            processed_files += 1
            logger.info(f"处理文件: {log_file['path']}")

            # 构建grep命令
            grep_cmd = build_grep_command(log_file['path'], start_dt, end_dt, ip_address, url_pattern, status_code)

            if grep_cmd:
                try:
                    # 执行grep命令
                    output = subprocess.run(grep_cmd, shell=True, capture_output=True, text=True, timeout=30)

                    if output.returncode == 0:
                        lines = output.stdout.strip().split('\n')
                        for line in lines:
                            if line.strip():
                                # 解析日志行时间
                                log_time = analyze_log_time(line, log_file['type'])
                                if log_time and start_dt <= log_time <= end_dt:
                                    all_matches.append(f"[{log_time.strftime('%Y-%m-%d %H:%M:%S')}] {line.strip()}")

                    # 如果已经达到最大行数，停止处理
                    if len(all_matches) >= max_lines:
                        all_matches = all_matches[:max_lines]
                        break

                except subprocess.TimeoutExpired:
                    logger.warning(f"处理文件超时: {log_file['path']}")
                except Exception as e:
                    logger.error(f"处理文件失败 {log_file['path']}: {e}")

        logger.info(f"处理了 {processed_files} 个文件，找到 {len(all_matches)} 条匹配记录")
        return all_matches[:max_lines]

    except Exception as e:
        logger.error(f'查询日志内容失败: {e}')
        return []

def is_file_in_time_range(log_file, start_dt, end_dt):
    """
    检查文件时间范围是否在查询范围内

    参数:
        log_file: 日志文件信息
        start_dt: 开始时间
        end_dt: 结束时间

    返回:
        bool: 是否在时间范围内
    """
    try:
        # 基于文件名和修改时间进行粗略判断
        mtime = datetime.fromtimestamp(log_file['mtime_timestamp'])

        # 如果文件修改时间早于开始时间，且不是当前日志文件，可以跳过
        if mtime < start_dt and 'access.log' not in log_file['path'] and 'error.log' not in log_file['path']:
            return False

        return True

    except Exception as e:
        logger.error(f'检查文件时间范围失败: {e}')
        return True  # 如果检查失败，默认处理该文件

def build_grep_command(log_path, start_dt, end_dt, ip_address, url_pattern, status_code):
    """
    构建grep命令

    参数:
        log_path: 日志文件路径
        start_dt: 开始时间
        end_dt: 结束时间
        ip_address: IP地址
        url_pattern: URL模式
        status_code: 状态码

    返回:
        str: grep命令字符串
    """
    try:
        # 基础命令
        cmd = f"zcat {log_path}" if log_path.endswith('.gz') else f"cat {log_path}"
        # 添加过滤条件
        filters = []

        # IP地址过滤
        if ip_address:
            filters.append(ip_address)

        # URL模式过滤（使用grep -E支持正则）
        if url_pattern:
            # 转义特殊字符
            url_pattern_escaped = re.escape(url_pattern)
            filters.append(url_pattern_escaped)

        # 状态码过滤（仅对访问日志有效）
        if status_code and 'access' in log_path:
            # 状态码通常在日志行的特定位置
            filters.append(f' {status_code} ')

        # 组合过滤条件
        if filters:
            if len(filters) == 1:
                cmd += f" | grep '{filters[0]}'"
            else:
                # 多个条件使用管道连接
                for filter_str in filters:
                    cmd += f" | grep '{filter_str}'"

        # 限制行数（避免处理过大文件）
        cmd += " | head -10000"  # 临时限制，避免内存问题

        return cmd

    except Exception as e:
        logger.error(f'构建grep命令失败: {e}')
        return None

def analyze_log_time(log_line, log_type):
    """
    解析日志行的时间戳

    参数:
        log_line: 日志行
        log_type: 日志类型

    返回:
        datetime: 解析出的时间
    """
    try:
        if log_type == 'access':
            # Nginx访问日志时间格式: [01/Jan/2023:00:00:00 +0800]
            time_pattern = r'\[(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})'  # NOSONAR
            match = re.search(time_pattern, log_line)  # NOSONAR
            if match:
                time_str = match.group(1)
                return datetime.strptime(time_str, '%d/%b/%Y:%H:%M:%S')

        elif log_type == 'error':
            # Nginx错误日志时间格式: 2023/01/01 00:00:00
            time_pattern = r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})'  # NOSONAR
            match = re.search(time_pattern, log_line)  # NOSONAR
            if match:
                time_str = match.group(1)
                return datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')

        # 如果无法解析，返回None
        return None

    except Exception as e:
        logger.error(f'解析日志时间失败: {e}')
        return None

def produce_statistics(log_content, log_type):
    """
    生成统计信息

    参数:
        log_content: 日志内容
        log_type: 日志类型

    返回:
        list: 统计信息列表
    """
    try:
        stats = []

        if log_type == 'access':
            # 访问日志统计
            status_codes = {}
            ip_addresses = {}
            urls = {}

            for line in log_content:
                # 解析状态码
                status_match = re.search(r' (\d{3}) ', line)  # NOSONAR
                if status_match:
                    state = status_match.group(1)
                    status_codes[state] = status_codes.get(state, 0) + 1

                # 解析IP地址
                ip_match = re.search(r'^[^\[]*\[[^\]]*\] (\S+)', line)  # NOSONAR
                if ip_match:
                    ip = ip_match.group(1)
                    ip_addresses[ip] = ip_addresses.get(ip, 0) + 1

                # 解析URL（简化版）
                url_match = re.search(r'\"(GET|POST|PUT|DELETE) ([^\s]+)', line)  # NOSONAR
                if url_match:
                    url = url_match.group(2)
                    urls[url] = urls.get(url, 0) + 1

            # 添加统计信息
            if status_codes:
                stats.append("状态码分布:")
                for code, count in sorted(status_codes.items(), key=lambda x: x[1], reverse=True)[:10]:
                    stats.append(f"  {code}: {count} 次")

            if ip_addresses:
                stats.append("IP访问统计 (前10):")
                for ip, count in sorted(ip_addresses.items(), key=lambda x: x[1], reverse=True)[:10]:
                    stats.append(f"  {ip}: {count} 次")

            if urls:
                stats.append("URL访问统计 (前10):")
                for url, count in sorted(urls.items(), key=lambda x: x[1], reverse=True)[:10]:
                    stats.append(f"  {url}: {count} 次")

        elif log_type == 'error':
            # 错误日志统计
            error_levels = {}

            for line in log_content:
                # 解析错误级别
                level_match = re.search(r'\[(emerg|alert|crit|error|warn|notice|info|debug)\]', line)  # NOSONAR
                if level_match:
                    level = level_match.group(1)
                    error_levels[level] = error_levels.get(level, 0) + 1

            if error_levels:
                stats.append("错误级别分布:")
                for level, count in sorted(error_levels.items(), key=lambda x: x[1], reverse=True):
                    stats.append(f"  {level}: {count} 次")

        if not stats:
            stats.append("无统计信息可用")

        return stats

    except Exception as e:
        logger.error(f'生成统计信息失败: {e}')
        return ["统计信息生成失败"]

def render_file_size(size_bytes):
    """
    格式化文件大小
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1

    return f"{size:.2f} {size_names[i]}"

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_log_history",
    "function": fetch_nginx_log_history,
    "description": "获取指定时间范围的历史日志，支持按时间/IP/URL/状态码过滤的MCP工具",
    "parameters": {
        "type": "object",
        "properties": {
            "start_time": {
                "type": "string",
                "description": "开始时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)，默认最近7天",
                "default": ""
            },
            "end_time": {
                "type": "string",
                "description": "结束时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)，默认当前时间",
                "default": ""
            },
            "ip_address": {
                "type": "string",
                "description": "IP地址过滤，支持部分匹配",
                "default": ""
            },
            "url_pattern": {
                "type": "string",
                "description": "URL模式过滤，支持正则表达式",
                "default": ""
            },
            "status_code": {
                "type": "string",
                "description": "状态码过滤 (如: 200, 404, 500)",
                "default": ""
            },
            "log_type": {
                "type": "string",
                "description": "日志类型：access（访问日志）、error（错误日志）",
                "enum": ["access", "error"],
                "default": "access"
            },
            "max_lines": {
                "type": "integer",
                "description": "最大返回行数",
                "minimum": 1,
                "maximum": 10000,
                "default": 1000
            }
        },
        "required": []
    }
}
