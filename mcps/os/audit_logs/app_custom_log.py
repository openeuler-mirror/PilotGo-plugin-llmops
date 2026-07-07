from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_app_custom')

def fetch_log_app_custom(log_path=None, keyword=None, error_only=False, last=None):
    """
    采集自定义应用日志（指定应用日志路径/最新内容/错误行/按关键字过滤）

    参数:
        log_path: 日志文件路径，如 "/var/log/nginx/access.log"
        keyword: 关键字，用于过滤日志
        error_only: 是否只显示错误行
        last: 显示最近的行数，如 "100"

    返回:
        格式化的自定义应用日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 自定义应用日志 ===')

        # 检查日志路径
        if not log_path:
            output.append('错误: 请指定日志文件路径')
            output.append('=====================')
            return '\n'.join(output)

        # 检查文件是否存在
        if not os.path.exists(log_path):
            output.append(f'错误: 日志文件 {log_path} 不存在')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'日志文件: {log_path}')

        # 获取日志内容
        try:
            logs = fetch_custom_log_content(log_path, keyword, error_only, last)
            if logs:
                output.append('\n日志内容:')
                output.append(logs)
            else:
                output.append('未检测到日志内容')
        except Exception as e:
            # 如果获取日志内容失败，直接返回错误
            logger.error(f'获取自定义应用日志内容失败: {e}')
            output.append('获取自定义应用日志失败')
            output.append('=====================')
            return '\n'.join(output)

        # 显示过滤条件
        filters = []
        if keyword:
            filters.append(f'关键字: {keyword}')
        if error_only:
            filters.append('只显示错误行')
        if last:
            filters.append(f'显示最近 {last} 行')

        if filters:
            output.append('\n过滤条件:')
            output.append(', '.join(filters))

        # 显示文件信息
        file_info = fetch_file_info(log_path)
        if file_info:
            output.append('\n文件信息:')
            for key, value in file_info.items():
                output.append(f"{key}: {value}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取自定义应用日志失败: {e}')
        return f'获取自定义应用日志失败: {e}'
