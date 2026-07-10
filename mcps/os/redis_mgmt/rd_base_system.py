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
def fetch_disk_info():
    """
    获取磁盘信息
    """
    disk_info = {}

    try:
        output = subprocess.run(['df', '-h'], capture_output=True, text=True)

        if output.returncode == 0:
            disk_info['磁盘使用情况'] = output.stdout.strip()

        output = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    disk_info['根文件系统'] = parts[0]
                    disk_info['总容量'] = parts[1]
                    disk_info['已使用'] = parts[2]
                    disk_info['可用容量'] = parts[3]
                    disk_info['使用率'] = parts[4]
                    disk_info['挂载点'] = parts[5]

        output = subprocess.run(['lsblk'], capture_output=True, text=True)

        if output.returncode == 0:
            disk_info['块设备信息'] = output.stdout.strip()

        output = subprocess.run(['fdisk', '-l', '2>/dev/null'], capture_output=True, text=True)

        if output.returncode == 0:
            disk_info['磁盘分区信息'] = output.stdout.strip()

        output = subprocess.run(['mount'], capture_output=True, text=True)

        if output.returncode == 0:
            mount_lines = output.stdout.split('\n')
            disk_info['挂载点数量'] = str(len(mount_lines))

        redis_pid = find_redis_pid()
        if redis_pid:
            cwd_path = f'/proc/{redis_pid}/cwd'
            if os.path.exists(cwd_path):
                output = subprocess.run(['df', '-h', cwd_path], capture_output=True, text=True)

                if output.returncode == 0:
                    lines = output.stdout.split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 5:
                            disk_info['Redis数据目录'] = parts[5]
                            disk_info['数据目录总容量'] = parts[1]
                            disk_info['数据目录已使用'] = parts[2]
                            disk_info['数据目录可用'] = parts[3]
                            disk_info['数据目录使用率'] = parts[4]

    except Exception as e:
        logger.error(f'获取磁盘信息失败: {e}')

    return disk_info
def fetch_dependencies_info():
    """
    获取依赖库版本
    """
    dependencies_info = {}

    try:
        libraries = [
            ('glibc', 'ldd', '--version'),
            ('openssl', 'openssl', 'version'),
            ('zlib', 'zlib-flate', '-h'),
            ('tcl', 'tclsh', 'info patchlevel'),
            ('jemalloc', 'jemalloc-config', '--version'),
            ('libevent', 'event-config', '--version'),
            ('libaio', 'rpm', '-q', 'libaio'),
            ('libgcc', 'rpm', '-q', 'libgcc'),
            ('libstdc++', 'rpm', '-q', 'libstdc++')
        ]

        for lib_name, cmd, *args in libraries:
            try:
                output = subprocess.run(
                    [cmd] + args,
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if output.returncode == 0:
                    output = output.stdout.strip()
                    if output:
                        dependencies_info[lib_name] = output.split('\n')[0]
            except Exception:
                pass

        output = subprocess.run(['ldd', '--version'], capture_output=True, text=True)

        if output.returncode == 0:
            version_line = output.stdout.split('\n')[0]
            dependencies_info['GLIBC'] = version_line

        output = subprocess.run(['openssl', 'version'], capture_output=True, text=True)

        if output.returncode == 0:
            dependencies_info['OpenSSL'] = output.stdout.strip()

        output = subprocess.run(['python3', '--version'], capture_output=True, text=True)

        if output.returncode == 0:
            dependencies_info['Python'] = output.stdout.strip()

        output = subprocess.run(['gcc', '--version'], capture_output=True, text=True)

        if output.returncode == 0:
            gcc_version = output.stdout.split('\n')[0]
            dependencies_info['GCC'] = gcc_version

        output = subprocess.run(['make', '--version'], capture_output=True, text=True)

        if output.returncode == 0:
            make_version = output.stdout.split('\n')[0]
            dependencies_info['Make'] = make_version

        redis_pid = find_redis_pid()
        if redis_pid:
            output = subprocess.run(['ldd', f'/proc/{redis_pid}/exe'], capture_output=True, text=True)

            if output.returncode == 0:
                dependencies_info['Redis动态链接库'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取依赖库版本失败: {e}')

    return dependencies_info
def fetch_redis_resource_usage(pid):
    """
    获取Redis资源使用情况
    """
    resource_usage = {}

    try:
        if os.path.exists(f'/proc/{pid}/status'):
            with open(f'/proc/{pid}/status', 'r') as f:
                status_lines = f.readlines()

            for line in status_lines:
                if line.startswith('VmPeak:'):
                    resource_usage['虚拟内存峰值'] = line.split(':')[1].strip()
                elif line.startswith('VmSize:'):
                    resource_usage['虚拟内存大小'] = line.split(':')[1].strip()
                elif line.startswith('VmRSS:'):
                    resource_usage['物理内存使用'] = line.split(':')[1].strip()
                elif line.startswith('VmData:'):
                    resource_usage['数据段大小'] = line.split(':')[1].strip()
                elif line.startswith('VmStk:'):
                    resource_usage['栈大小'] = line.split(':')[1].strip()
                elif line.startswith('VmExe:'):
                    resource_usage['代码段大小'] = line.split(':')[1].strip()
                elif line.startswith('VmLib:'):
                    resource_usage['库大小'] = line.split(':')[1].strip()
                elif line.startswith('Threads:'):
                    resource_usage['线程数'] = line.split(':')[1].strip()

        if os.path.exists(f'/proc/{pid}/stat'):
            with open(f'/proc/{pid}/stat', 'r') as f:
                stat_data = f.read().split()

            if len(stat_data) > 13:
                utime = int(stat_data[13])
                stime = int(stat_data[14])
                total_time = utime + stime
                resource_usage['CPU时间(用户态)'] = f"{utime} jiffies"
                resource_usage['CPU时间(内核态)'] = f"{stime} jiffies"
                resource_usage['总CPU时间'] = f"{total_time} jiffies"

        output = subprocess.run(['ps', '-p', pid, '-o', 'pcpu,rss,vsz,etime'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    resource_usage['CPU使用率'] = f"{parts[0]}%"
                    resource_usage['物理内存(KB)'] = parts[1]
                    resource_usage['虚拟内存(KB)'] = parts[2]
                    resource_usage['运行时长'] = parts[3]

        output = subprocess.run(['redis-cli', 'INFO', 'memory'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('used_memory:'):
                    resource_usage['已用内存(字节)'] = line.split(':')[1]
                elif line.startswith('used_memory_human:'):
                    resource_usage['已用内存'] = line.split(':')[1]
                elif line.startswith('used_memory_rss:'):
                    resource_usage['RSS内存(字节)'] = line.split(':')[1]
                elif line.startswith('used_memory_rss_human:'):
                    resource_usage['RSS内存'] = line.split(':')[1]
                elif line.startswith('used_memory_peak:'):
                    resource_usage['内存峰值(字节)'] = line.split(':')[1]
                elif line.startswith('used_memory_peak_human:'):
                    resource_usage['内存峰值'] = line.split(':')[1]
                elif line.startswith('used_memory_lua:'):
                    resource_usage['Lua内存(字节)'] = line.split(':')[1]
                elif line.startswith('mem_fragmentation_ratio:'):
                    resource_usage['内存碎片率'] = line.split(':')[1]

    except Exception as e:
        logger.error(f'获取Redis资源使用情况失败: {e}')

    return resource_usage

TOOL_CONFIG = {
    "name": "fetch_redis_base_system",
    "function": fetch_redis_base_system,
    "description": "采集Redis运行环境（OS/内核版本、CPU/内存/磁盘信息）、系统依赖库版本",
    "parameters": {
        "type": "object",
        "properties": {
            "system_type": {
                "type": "string",
                "description": "指定要采集的系统信息类型，可选值：os（操作系统信息）、cpu（CPU信息）、memory（内存信息）、disk（磁盘信息）、dependencies（依赖库版本）、all（所有系统信息）",
                "enum": ["os", "cpu", "memory", "disk", "dependencies", "all"]
            }
        },
        "required": []
    }
}
