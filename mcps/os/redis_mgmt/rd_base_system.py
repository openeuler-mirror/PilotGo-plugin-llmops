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
logger = logging.getLogger('redis_base_system')

def fetch_redis_base_system(system_type=None):
    """
    采集Redis运行环境（OS/内核版本、CPU/内存/磁盘信息）、系统依赖库版本

    参数:
        system_type: 指定要采集的系统信息类型，可选值：
                     - "os": 仅采集操作系统信息
                     - "cpu": 仅采集CPU信息
                     - "memory": 仅采集内存信息
                     - "disk": 仅采集磁盘信息
                     - "dependencies": 仅采集依赖库版本
                     - "all": 采集所有系统信息（默认）

    返回:
        格式化的Redis系统环境信息字符串
    """
    try:
        output = []
        output.append('=== Redis系统环境信息 ===')

        redis_pid = find_redis_pid()

        if redis_pid:
            output.append(f'检测到Redis进程: PID {redis_pid}')
        else:
            output.append('未检测到运行中的Redis进程')
            output.append('采集系统基础环境信息...')

        if system_type is None or system_type == "all" or system_type == "os":
            os_info = fetch_os_info()
            if os_info:
                output.append('\n操作系统信息:')
                for key, val in os_info.items():
                    output.append(f"  {key}: {val}")

        if system_type is None or system_type == "all" or system_type == "cpu":
            proc_data = fetch_cpu_info()
            if proc_data:
                output.append('\nCPU信息:')
                for key, val in proc_data.items():
                    output.append(f"  {key}: {val}")

        if system_type is None or system_type == "all" or system_type == "memory":
            memory_info = fetch_memory_info()
            if memory_info:
                output.append('\n内存信息:')
                for key, val in memory_info.items():
                    output.append(f"  {key}: {val}")

        if system_type is None or system_type == "all" or system_type == "disk":
            disk_info = fetch_disk_info()
            if disk_info:
                output.append('\n磁盘信息:')
                for key, val in disk_info.items():
                    output.append(f"  {key}: {val}")

        if system_type is None or system_type == "all" or system_type == "dependencies":
            dependencies_info = fetch_dependencies_info()
            if dependencies_info:
                output.append('\n依赖库版本:')
                for key, val in dependencies_info.items():
                    output.append(f"  {key}: {val}")

        if redis_pid:
            resource_usage = fetch_redis_resource_usage(redis_pid)
            if resource_usage:
                output.append('\nRedis资源使用:')
                for key, val in resource_usage.items():
                    output.append(f"  {key}: {val}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis系统环境信息失败: {e}')
        return f'获取Redis系统环境信息失败: {e}'
def fetch_os_info():
    """
    获取操作系统信息
    """
    os_info = {}

    try:
        output = subprocess.run(['uname', '-a'], capture_output=True, text=True)

        if output.returncode == 0:
            os_info['系统信息'] = output.stdout.strip()

        output = subprocess.run(['uname', '-r'], capture_output=True, text=True)

        if output.returncode == 0:
            os_info['内核版本'] = output.stdout.strip()

        output = subprocess.run(['uname', '-m'], capture_output=True, text=True)

        if output.returncode == 0:
            os_info['系统架构'] = output.stdout.strip()

        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('NAME='):
                        os_info['操作系统名称'] = line.split('=')[1].strip('"')
                    elif line.startswith('VERSION='):
                        os_info['系统版本'] = line.split('=')[1].strip('"')
                    elif line.startswith('ID='):
                        os_info['系统ID'] = line.split('=')[1].strip('"')

        if os.path.exists('/etc/lsb-release'):
            with open('/etc/lsb-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('DISTRIB_ID='):
                        os_info['发行版ID'] = line.split('=')[1].strip('"')
                    elif line.startswith('DISTRIB_RELEASE='):
                        os_info['发行版版本'] = line.split('=')[1].strip('"')
                    elif line.startswith('DISTRIB_DESCRIPTION='):
                        os_info['发行版描述'] = line.split('=')[1].strip('"')

        if os.path.exists('/etc/redhat-release'):
            with open('/etc/redhat-release', 'r') as f:
                os_info['RedHat版本'] = f.read().strip()

        output = subprocess.run(['uptime'], capture_output=True, text=True)

        if output.returncode == 0:
            os_info['系统运行时间'] = output.stdout.strip()

        output = subprocess.run(['hostname'], capture_output=True, text=True)

        if output.returncode == 0:
            os_info['主机名'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取操作系统信息失败: {e}')

    return os_info
