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
