from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_secure')

def fetch_log_secure(ip=None, user=None, since=None, until=None):
    """
    采集安全日志内容（/var/log/secure/认证/登录/权限变更/SSH日志/按IP/用户过滤）

    参数:
        ip: IP地址，如 "192.168.1.1"
        user: 用户名，如 "root"
        since: 起始时间，如 "1h ago", "2023-01-01"
        until: 结束时间，如 "now", "2023-01-02"

    返回:
        格式化的安全日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 安全日志内容 ===')

        # 确定安全日志文件路径
        secure_logs = [
            '/var/log/secure',
            '/var/log/auth.log'
        ]

        log_file = None
        for log in secure_logs:
            if os.path.exists(log):
                log_file = log
                break

        if not log_file:
            output.append('未检测到安全日志文件')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'日志文件: {log_file}')

        # 获取日志内容
        logs = fetch_secure_log_content(log_file, ip, user, since, until)
        if logs:
            output.append('\n日志内容:')
            output.append(logs)
        else:
            output.append('未检测到日志内容')

        # 显示过滤条件
        filters = []
        if ip:
            filters.append(f'IP: {ip}')
        if user:
            filters.append(f'用户: {user}')
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
        logger.error(f'获取安全日志内容失败: {e}')
        return f'获取安全日志内容失败: {e}'

def fetch_secure_log_content(log_file, ip=None, user=None, since=None, until=None):
    """
    获取安全日志内容
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
            # 按IP过滤
            if ip and ip not in line:
                continue

            # 按用户过滤
            if user and user not in line:
                continue

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

            filtered_lines.append(line)

        # 只返回最后50行
        return ''.join(filtered_lines[-50:])

    except Exception as e:
        logger.error(f'获取安全日志内容失败: {e}')
        raise  # 重新抛出异常，让上级函数处理

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_secure",
    "function": fetch_log_secure,
    "description": "采集安全日志内容（/var/log/secure/认证/登录/权限变更/SSH日志/按IP/用户过滤）",
    "parameters": {
        "type": "object",
        "properties": {
            "ip": {
                "type": "string",
                "description": "IP地址，如 \"192.168.1.1\""
            },
            "user": {
                "type": "string",
                "description": "用户名，如 \"root\""
            },
            "since": {
                "type": "string",
                "description": "起始时间，如 \"1h ago\", \"2023-01-01\""
            },
            "until": {
                "type": "string",
                "description": "结束时间，如 \"now\", \"2023-01-02\""
            }
        },
        "required": []
    }
}
