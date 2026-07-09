from datetime import datetime
import logging
import os
import re
import subprocess

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('redis_base_service')

def fetch_redis_base_service(service_type=None):
    """
    采集Redis系统服务状态（开机自启/手动）、服务管理脚本路径、重启策略

    参数:
        service_type: 指定要采集的服务信息类型，可选值：
                      - "status": 仅采集服务状态
                      - "autostart": 仅采集开机自启状态
                      - "script": 仅采集服务管理脚本路径
                      - "restart": 仅采集重启策略
                      - "all": 采集所有服务信息（默认）

    返回:
        格式化的Redis服务信息字符串
    """
    try:
        output = []
        output.append('=== Redis服务信息 ===')

        redis_pid = find_redis_pid()

        if redis_pid:
            output.append(f'检测到Redis进程: PID {redis_pid}')
        else:
            output.append('未检测到运行中的Redis进程')
            output.append('采集Redis服务配置信息...')

        if service_type is None or service_type == "all" or service_type == "status":
            status_info = fetch_service_status()
            if status_info:
                output.append('\n服务状态:')
                for key, value in status_info.items():
                    output.append(f"  {key}: {value}")

        if service_type is None or service_type == "all" or service_type == "autostart":
            autostart_info = fetch_autostart_status()
            if autostart_info:
                output.append('\n开机自启状态:')
                for key, value in autostart_info.items():
                    output.append(f"  {key}: {value}")

        if service_type is None or service_type == "all" or service_type == "script":
            script_info = fetch_service_script()
            if script_info:
                output.append('\n服务管理脚本:')
                for key, value in script_info.items():
                    output.append(f"  {key}: {value}")

        if service_type is None or service_type == "all" or service_type == "restart":
            restart_info = fetch_restart_policy()
            if restart_info:
                output.append('\n重启策略:')
                for key, value in restart_info.items():
                    output.append(f"  {key}: {value}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis服务信息失败: {e}')
        return f'获取Redis服务信息失败: {e}'
