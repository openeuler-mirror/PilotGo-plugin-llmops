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
def fetch_service_status():
    """
    获取服务状态
    """
    status_info = {}

    try:
        redis_pid = find_redis_pid()

        if redis_pid:
            status_info['进程状态'] = '运行中'
            status_info['进程PID'] = redis_pid
        else:
            status_info['进程状态'] = '未运行'

        service_names = ['redis', 'redis-server', 'redis_6379', 'redis.service']

        for service_name in service_names:
            output = subprocess.run(['systemctl', 'is-active', service_name], capture_output=True, text=True)

            if output.returncode == 0 or output.returncode == 3:
                status_info['Systemd服务状态'] = output.stdout.strip()
                status_info['Systemd服务名称'] = service_name
                break

        for service_name in service_names:
            output = subprocess.run(['service', service_name, 'status'], capture_output=True, text=True)

            if output.returncode == 0 or output.returncode == 3:
                status_info['SysV服务状态'] = '已配置'
                status_info['SysV服务名称'] = service_name
                break

        output = subprocess.run(['systemctl', 'is-enabled', 'redis.service'], capture_output=True, text=True)

        if output.returncode == 0:
            status_info['Systemd启用状态'] = output.stdout.strip()
        elif output.returncode == 1:
            status_info['Systemd启用状态'] = 'disabled'

        output = subprocess.run(['systemctl', 'is-enabled', 'redis-server.service'], capture_output=True, text=True)

        if output.returncode == 0:
            status_info['Redis-Server启用状态'] = output.stdout.strip()
        elif output.returncode == 1:
            status_info['Redis-Server启用状态'] = 'disabled'

        output = subprocess.run(['systemctl', 'status', 'redis.service'], capture_output=True, text=True)

        if output.returncode == 0 or output.returncode == 3:
            output = output.stdout
            if 'Active: active (running)' in output:
                status_info['详细状态'] = '运行中'
            elif 'Active: inactive (dead)' in output:
                status_info['详细状态'] = '已停止'
            elif 'Active: failed' in output:
                status_info['详细状态'] = '失败'
            else:
                status_info['详细状态'] = '未知'

            if 'Loaded: loaded' in output:
                match = re.search(r'Loaded: loaded \(([^;]+);', output)  # NOSONAR
                if match:
                    status_info['服务单元文件'] = match.group(1)

            if 'Main PID:' in output:
                match = re.search(r'Main PID: (\d+)', output)  # NOSONAR
                if match:
                    status_info['主进程PID'] = match.group(1)

        output = subprocess.run(
            ['systemctl', 'list-units', '--type=service', '|', 'grep', '-i', 'redis'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            redis_services = output.stdout.strip().split('\n')
            status_info['Redis相关服务'] = f"{len(redis_services)} 个"
            for i, service in enumerate(redis_services, 1):
                status_info[f'服务{i}'] = service.strip()

        output = subprocess.run(
            ['ps', 'aux', '|', 'grep', 'redis-server', '|', 'grep', '-v', 'grep'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            redis_processes = output.stdout.strip().split('\n')
            status_info['Redis进程数'] = str(len(redis_processes))

            for i, process in enumerate(redis_processes, 1):
                parts = process.split()
                if len(parts) >= 2:
                    status_info[f'进程{i}'] = f"PID: {parts[1]}, 用户: {parts[0]}"

        output = subprocess.run(
            ['redis-cli', 'PING'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            status_info['Redis响应'] = output.stdout.strip()
            status_info['Redis服务'] = '正常'
        else:
            status_info['Redis服务'] = '异常或未运行'

    except Exception as e:
        logger.error(f'获取服务状态失败: {e}')

    return status_info
