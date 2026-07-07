from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_syslog_content')

def fetch_log_syslog_content(log_file=None, since=None, until=None, level=None):
    """
    采集系统日志内容（/var/log/messages/syslog/auth.log/按时间/级别过滤）

    参数:
        log_file: 日志文件路径，如 "/var/log/messages", "/var/log/syslog"
        since: 起始时间，如 "1h ago", "2023-01-01"
        until: 结束时间，如 "now", "2023-01-02"
        level: 日志级别，如 "error", "warn", "info"

    返回:
        格式化的系统日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 系统日志内容 ===')

        # 确定要检查的日志文件
        log_files = []
        if log_file:
            # 检查文件是否存在
            if os.path.exists(log_file):
                log_files.append(log_file)
            else:
                output.append(f'错误: 日志文件 {log_file} 不存在')
                output.append('=====================')
                return '\n'.join(output)
        else:
            # 默认检查常见系统日志文件
            default_logs = [
                '/var/log/messages',
                '/var/log/syslog',
                '/var/log/auth.log',
                '/var/log/daemon.log'
            ]

            for log in default_logs:
                if os.path.exists(log):
                    log_files.append(log)

        if not log_files:
            output.append('未检测到系统日志文件')
            output.append('=====================')
            return '\n'.join(output)

        # 处理每个日志文件
        for log_file_path in log_files:
            output.append(f'\n=== 日志文件: {log_file_path} ===')

            # 获取日志内容
            logs = fetch_log_content(log_file_path, since, until, level)
            if logs:
                output.append('\n日志内容:')
                output.append(logs)
            else:
                output.append('未检测到日志内容')

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取系统日志内容失败: {e}')
        return f'获取系统日志内容失败: {e}'

def fetch_log_content(log_file, since=None, until=None, level=None):
    """
    获取日志文件内容
    """
    try:
        # 计算时间范围
        start_time = None
        end_time = None

        if since:
            if 'ago' in since:
                # 解析相对时间
                parts = since.split()
                if len(parts) == 2:
                    val = int(parts[0])
                    unit = parts[1].rstrip('s')

                    delta = timedelta()
                    if unit == 'h':
                        delta = timedelta(hours=val)
                    elif unit == 'd':
                        delta = timedelta(days=val)
                    elif unit == 'm':
                        delta = timedelta(minutes=val)

                    start_time = datetime.now() - delta
            else:
                # 解析绝对时间
                try:
                    start_time = datetime.strptime(since, '%Y-%m-%d')
                except ValueError:
                    pass

        if until:
            if until == 'now':
                end_time = datetime.now()
            else:
                try:
                    end_time = datetime.strptime(until, '%Y-%m-%d')
                except ValueError:
                    pass

        # 读取日志文件
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 过滤日志
        filtered_lines = []
        for line in lines:
            # 按时间过滤
            if start_time or end_time:
                # 尝试解析时间戳
                timestamp_match = re.search(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)  # NOSONAR
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    try:
                        # 构建完整日期
                        current_year = datetime.now().year
                        timestamp = datetime.strptime(f'{current_year} {timestamp_str}', '%Y %b %d %H:%M:%S')

                        # 检查时间范围
                        if start_time and timestamp < start_time:
                            continue
                        if end_time and timestamp > end_time:
                            continue
                    except ValueError:
                        pass

            # 按级别过滤
            if level:
                level_pattern = re.compile(r'\b(' + level + r')\b', re.IGNORECASE)  # NOSONAR
                if not level_pattern.search(line):
                    continue

            filtered_lines.append(line)

        # 只返回最后50行
        return ''.join(filtered_lines[-50:])

    except Exception as e:
        logger.error(f'获取日志内容失败: {e}')
        raise  # 重新抛出异常，让上级函数处理

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_syslog_content",
    "function": fetch_log_syslog_content,
    "description": "采集系统日志内容（/var/log/messages/syslog/auth.log/按时间/级别过滤）",
    "parameters": {
        "type": "object",
        "properties": {
            "log_file": {
                "type": "string",
                "description": "日志文件路径，如 \"/var/log/messages\", \"/var/log/syslog\""
            },
            "since": {
                "type": "string",
                "description": "起始时间，如 \"1h ago\", \"2023-01-01\""
            },
            "until": {
                "type": "string",
                "description": "结束时间，如 \"now\", \"2023-01-02\""
            },
            "level": {
                "type": "string",
                "description": "日志级别，如 \"error\", \"warn\", \"info\""
            }
        },
        "required": []
    }
}
