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
def fetch_cpu_info():
    """
    获取CPU信息
    """
    proc_data = {}

    try:
        if os.path.exists('/proc/cpuinfo'):
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo_lines = f.readlines()

            cpu_count = 0
            physical_cpus = set()
            cpu_cores = {}

            for line in cpuinfo_lines:
                if line.startswith('processor'):
                    cpu_count += 1
                elif line.startswith('physical id'):
                    physical_id = line.split(':')[1].strip()
                    physical_cpus.add(physical_id)
                elif line.startswith('cpu cores'):
                    cores = line.split(':')[1].strip()
                    cpu_cores['核心数'] = cores
                elif line.startswith('model name'):
                    proc_data['CPU型号'] = line.split(':')[1].strip()
                elif line.startswith('cpu MHz'):
                    proc_data['CPU频率'] = f"{line.split(':')[1].strip()} MHz"
                elif line.startswith('cache size'):
                    proc_data['缓存大小'] = line.split(':')[1].strip()
                elif line.startswith('vendor_id'):
                    proc_data['厂商ID'] = line.split(':')[1].strip()

            proc_data['逻辑CPU数'] = cpu_count
            proc_data['物理CPU数'] = len(physical_cpus)

            if physical_cpus and cpu_count > 0:
                proc_data['每物理CPU核心数'] = cpu_count // len(physical_cpus)

        output = subprocess.run(['lscpu'], capture_output=True, text=True)

        if output.returncode == 0:
            lscpu_lines = output.stdout.split('\n')
            for line in lscpu_lines:
                if 'CPU(s):' in line and 'On-line CPU(s)' not in line:
                    proc_data['CPU总数'] = line.split(':')[1].strip()
                elif 'Thread(s) per core:' in line:
                    proc_data['每核心线程数'] = line.split(':')[1].strip()
                elif 'Core(s) per socket:' in line:
                    proc_data['每插槽核心数'] = line.split(':')[1].strip()
                elif 'Socket(s):' in line:
                    proc_data['CPU插槽数'] = line.split(':')[1].strip()
                elif 'CPU MHz:' in line:
                    proc_data['当前CPU频率'] = line.split(':')[1].strip()
                elif 'CPU max MHz:' in line:
                    proc_data['最大CPU频率'] = line.split(':')[1].strip()
                elif 'CPU min MHz:' in line:
                    proc_data['最小CPU频率'] = line.split(':')[1].strip()

        if os.path.exists('/proc/loadavg'):
            with open('/proc/loadavg', 'r') as f:
                loadavg = f.read().strip().split()
                if loadavg:
                    proc_data['1分钟负载'] = loadavg[0]
                    proc_data['5分钟负载'] = loadavg[1]
                    proc_data['15分钟负载'] = loadavg[2]

        output = subprocess.run(['nproc'], capture_output=True, text=True)

        if output.returncode == 0:
            proc_data['可用CPU数'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取CPU信息失败: {e}')

    return proc_data
def fetch_memory_info():
    """
    获取内存信息
    """
    memory_info = {}

    try:
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo', 'r') as f:
                meminfo_lines = f.readlines()

            mem_data = {}
            for line in meminfo_lines:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem_data[key] = int(val)

            if 'MemTotal' in mem_data:
                memory_info['总内存'] = render_memory_size(mem_data['MemTotal'])
            if 'MemFree' in mem_data:
                memory_info['空闲内存'] = render_memory_size(mem_data['MemFree'])
            if 'MemAvailable' in mem_data:
                memory_info['可用内存'] = render_memory_size(mem_data['MemAvailable'])
            if 'Buffers' in mem_data:
                memory_info['缓冲区'] = render_memory_size(mem_data['Buffers'])
            if 'Cached' in mem_data:
                memory_info['缓存'] = render_memory_size(mem_data['Cached'])
            if 'SwapTotal' in mem_data:
                memory_info['总交换空间'] = render_memory_size(mem_data['SwapTotal'])
            if 'SwapFree' in mem_data:
                memory_info['空闲交换空间'] = render_memory_size(mem_data['SwapFree'])

            if 'MemTotal' in mem_data and 'MemAvailable' in mem_data:
                used_percent = ((mem_data['MemTotal'] - mem_data['MemAvailable']) / mem_data['MemTotal']) * 100
                memory_info['内存使用率'] = f"{used_percent:.2f}%"

            if 'SwapTotal' in mem_data and 'SwapFree' in mem_data:
                if mem_data['SwapTotal'] > 0:
                    swap_used_percent = ((mem_data['SwapTotal'] - mem_data['SwapFree']) / mem_data['SwapTotal']) * 100
                    memory_info['交换空间使用率'] = f"{swap_used_percent:.2f}%"

        output = subprocess.run(['free', '-h'], capture_output=True, text=True)

        if output.returncode == 0:
            memory_info['内存概览'] = output.stdout.strip()

        output = subprocess.run(['vmstat', '-s'], capture_output=True, text=True)

        if output.returncode == 0:
            vmstat_lines = output.stdout.split('\n')
            for line in vmstat_lines:
                if 'total memory' in line.lower():
                    memory_info['总内存(KB)'] = line.split()[0]
                elif 'used memory' in line.lower():
                    memory_info['已用内存(KB)'] = line.split()[0]
                elif 'free memory' in line.lower():
                    memory_info['空闲内存(KB)'] = line.split()[0]

    except Exception as e:
        logger.error(f'获取内存信息失败: {e}')

    return memory_info
def render_memory_size(kb):
    """
    格式化内存大小
    """
    mb = kb / 1024
    gb = mb / 1024

    if gb >= 1:
        return f"{gb:.2f} GB"
    elif mb >= 1:
        return f"{mb:.2f} MB"
    else:
        return f"{kb} KB"
