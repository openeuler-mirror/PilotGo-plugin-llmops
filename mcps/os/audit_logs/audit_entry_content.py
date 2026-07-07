from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_audit_content')

def fetch_log_audit_content(since=None, until=None, type=None):
    """
    采集审计日志内容（/var/log/audit/审计事件/用户操作/文件变更/系统调用）

    参数:
        since: 起始时间，如 "1h ago", "2023-01-01"
        until: 结束时间，如 "now", "2023-01-02"
        type: 事件类型，如 "user", "file", "syscall"

    返回:
        格式化的审计日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 审计日志内容 ===')

        # 检查审计日志目录
        audit_log_dir = '/var/log/audit'
        if not os.path.exists(audit_log_dir) or not os.path.isdir(audit_log_dir):
            output.append('未检测到审计日志目录')
            output.append('=====================')
            return '\n'.join(output)

        # 添加日志目录信息
        output.append(f'日志目录: {audit_log_dir}')

        # 获取审计日志文件
        audit_logs = [os.path.join(audit_log_dir, file) for file in os.listdir(audit_log_dir) if file.startswith('audit.log')]

        if not audit_logs:
            output.append('未检测到审计日志文件')
            output.append('=====================')
            return '\n'.join(output)

        # 按修改时间排序，最新的在前
        audit_logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # 只处理最新的几个日志文件
        recent_logs = audit_logs[:3]

        # 处理每个日志文件
        for log_file in recent_logs:
            output.append(f'\n=== 日志文件: {log_file} ===')

            # 获取日志内容
            try:
                logs = fetch_audit_log_content(log_file, since, until, type)
                if logs:
                    output.append('\n日志内容:')
                    output.append(logs)
                else:
                    output.append('未检测到日志内容')
            except Exception as e:
                logger.error(f'获取审计日志内容失败: {e}')
                output.append('获取审计日志内容失败')

        # 显示过滤条件
        filters = []
        if type:
            filters.append(f'事件类型: {type}')
        if since:
            filters.append(f'起始时间: {since}')
        if until:
            filters.append(f'结束时间: {until}')

        if filters:
            output.append('\n过滤条件:')
            output.append(', '.join(filters))

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取审计日志内容失败: {e}')
        return f'获取审计日志内容失败: {e}'
def fetch_audit_log_content(log_file, since=None, until=None, type=None):
    """
    获取审计日志内容
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
        with open(log_file, 'r') as f:
            lines = f.readlines()

        # 过滤日志
        filtered_lines = []
        for line in lines:
            # 按事件类型过滤
            if type:
                if type == 'user' and 'type=USER' not in line:
                    continue
                elif type == 'file' and 'type=PATH' not in line:
                    continue
                elif type == 'syscall' and 'type=SYSCALL' not in line:
                    continue

            # 按时间过滤
            if start_time or end_time:
                # 尝试解析时间戳
                timestamp_match = re.search(r'time=(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6})', line)  # NOSONAR
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')

                        # 检查时间范围
                        if start_time and timestamp < start_time:
                            continue
                        if end_time and timestamp > end_time:
                            continue
                    except ValueError:
                        pass

            filtered_lines.append(line)

        # 只返回最后50行
        return ''.join(filtered_lines[-50:])

    except Exception as e:
        logger.error(f'获取审计日志内容失败: {e}')
        raise  # 抛出异常，让调用者处理

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_audit_content",
    "function": fetch_log_audit_content,
    "description": "采集审计日志内容（/var/log/audit/审计事件/用户操作/文件变更/系统调用）",
    "parameters": {
        "type": "object",
        "properties": {
            "since": {
                "type": "string",
                "description": "起始时间，如 \"1h ago\", \"2023-01-01\""
            },
            "until": {
                "type": "string",
                "description": "结束时间，如 \"now\", \"2023-01-02\""
            },
            "type": {
                "type": "string",
                "description": "事件类型，如 \"user\", \"file\", \"syscall\""
            }
        },
        "required": []
    }
}
