from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_cron')

def fetch_log_cron(since=None, until=None, user=None):
    """
    采集定时任务日志（/var/log/cron/cron.log/定时任务执行/失败/时间/用户）

    参数:
        since: 起始时间，如 "1h ago", "2023-01-01"
        until: 结束时间，如 "now", "2023-01-02"
        user: 用户名，如 "root"

    返回:
        格式化的定时任务日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 定时任务日志内容 ===')

        # 确定定时任务日志文件路径
        cron_logs = [
            '/var/log/cron',
            '/var/log/cron.log',
            '/var/log/syslog'
        ]

        log_file = None
        for log in cron_logs:
            if os.path.exists(log):
                log_file = log
                break

        if not log_file:
            output.append('未检测到定时任务日志文件')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'日志文件: {log_file}')

        # 获取日志内容
        logs = fetch_cron_log_content(log_file, since, until, user)
        if logs:
            output.append('\n日志内容:')
            output.append(logs)
        else:
            output.append('未检测到日志内容')

        # 显示过滤条件
        filters = []
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
        logger.error(f'获取定时任务日志内容失败: {e}')
        return f'获取定时任务日志内容失败: {e}'
