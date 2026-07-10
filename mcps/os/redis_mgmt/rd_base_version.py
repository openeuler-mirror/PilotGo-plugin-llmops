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
logger = logging.getLogger('redis_base_version')

def fetch_redis_base_version(info_type=None):
    """
    采集Redis版本、编译参数、内核适配信息、支持的模块

    参数:
        info_type: 指定要采集的信息类型，可选值：
                   - "version": 仅采集版本信息
                   - "compile": 仅采集编译参数
                   - "kernel": 仅采集内核适配信息
                   - "modules": 仅采集支持的模块
                   - "all": 采集所有信息（默认）

    返回:
        格式化的Redis版本信息字符串
    """
    try:
        output = []
        output.append('=== Redis版本信息 ===')

        redis_pid = find_redis_pid()

        if not redis_pid:
            output.append('未检测到运行中的Redis进程')
            output.append('尝试通过redis-cli命令获取信息...')

            ver_data = fetch_redis_version_via_cli()
            if ver_data:
                output.append('\nRedis版本:')
                for key, value in ver_data.items():
                    output.append(f"  {key}: {value}")
            else:
                output.append('无法获取Redis版本信息，请确认Redis是否已安装或正在运行')

            output.append('=====================')
            return '\n'.join(output)

        output.append(f'检测到Redis进程: PID {redis_pid}')

        if info_type is None or info_type == "all" or info_type == "version":
            ver_data = fetch_redis_version_info(redis_pid)
            if ver_data:
                output.append('\nRedis版本:')
                for key, value in ver_data.items():
                    output.append(f"  {key}: {value}")

        if info_type is None or info_type == "all" or info_type == "compile":
            build_info = fetch_redis_compile_info(redis_pid)
            if build_info:
                output.append('\n编译参数:')
                for key, value in build_info.items():
                    output.append(f"  {key}: {value}")

        if info_type is None or info_type == "all" or info_type == "kernel":
            kern_info = fetch_redis_kernel_info(redis_pid)
            if kern_info:
                output.append('\n内核适配信息:')
                for key, value in kern_info.items():
                    output.append(f"  {key}: {value}")

        if info_type is None or info_type == "all" or info_type == "modules":
            modules_info = fetch_redis_modules_info(redis_pid)
            if modules_info:
                output.append('\n支持的模块:')
                for key, value in modules_info.items():
                    output.append(f"  {key}: {value}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis版本信息失败: {e}')
        return f'获取Redis版本信息失败: {e}'
def fetch_redis_version_via_cli():
    """
    通过redis-cli获取版本信息
    """
    ver_data = {}

    try:
        output = subprocess.run(['redis-cli', '--version'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            ver_str = output.stdout.strip()
            ver_data['版本字符串'] = ver_str

            ver_match = re.search(r'v(\d+\.\d+\.\d+)', ver_str)  # NOSONAR
            if ver_match:
                ver_data['主版本号'] = ver_match.group(1)

        output = subprocess.run(['redis-cli', 'INFO', 'server'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('redis_version:'):
                    ver_data['Redis版本'] = line.split(':')[1]
                elif line.startswith('redis_git_sha1:'):
                    ver_data['Git SHA1'] = line.split(':')[1]
                elif line.startswith('redis_git_dirty:'):
                    ver_data['Git Dirty'] = line.split(':')[1]
                elif line.startswith('redis_build_id:'):
                    ver_data['Build ID'] = line.split(':')[1]
                elif line.startswith('os:'):
                    ver_data['操作系统'] = line.split(':')[1]
                elif line.startswith('arch_bits:'):
                    ver_data['架构位数'] = line.split(':')[1]
                elif line.startswith('multiplexing_api:'):
                    ver_data['多路复用API'] = line.split(':')[1]
                elif line.startswith('gcc_version:'):
                    ver_data['GCC版本'] = line.split(':')[1]
                elif line.startswith('process_id:'):
                    ver_data['进程ID'] = line.split(':')[1]
                elif line.startswith('run_id:'):
                    ver_data['运行ID'] = line.split(':')[1]
                elif line.startswith('tcp_port:'):
                    ver_data['TCP端口'] = line.split(':')[1]
                elif line.startswith('uptime_in_seconds:'):
                    ver_data['运行时长(秒)'] = line.split(':')[1]
                elif line.startswith('uptime_in_days:'):
                    ver_data['运行时长(天)'] = line.split(':')[1]

    except Exception as e:
        logger.error(f'通过redis-cli获取版本信息失败: {e}')

    return ver_data
def fetch_redis_version_info(pid):
    """
    获取Redis版本信息
    """
    ver_data = {}

    try:
        output = subprocess.run(['redis-cli', 'INFO', 'server'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('redis_version:'):
                    ver_data['Redis版本'] = line.split(':')[1]
                elif line.startswith('redis_git_sha1:'):
                    ver_data['Git SHA1'] = line.split(':')[1]
                elif line.startswith('redis_git_dirty:'):
                    ver_data['Git Dirty'] = line.split(':')[1]
                elif line.startswith('redis_build_id:'):
                    ver_data['Build ID'] = line.split(':')[1]
                elif line.startswith('os:'):
                    ver_data['操作系统'] = line.split(':')[1]
                elif line.startswith('arch_bits:'):
                    ver_data['架构位数'] = line.split(':')[1]
                elif line.startswith('multiplexing_api:'):
                    ver_data['多路复用API'] = line.split(':')[1]
                elif line.startswith('gcc_version:'):
                    ver_data['GCC版本'] = line.split(':')[1]
                elif line.startswith('process_id:'):
                    ver_data['进程ID'] = line.split(':')[1]
                elif line.startswith('run_id:'):
                    ver_data['运行ID'] = line.split(':')[1]
                elif line.startswith('tcp_port:'):
                    ver_data['TCP端口'] = line.split(':')[1]
                elif line.startswith('uptime_in_seconds:'):
                    ver_data['运行时长(秒)'] = line.split(':')[1]
                elif line.startswith('uptime_in_days:'):
                    ver_data['运行时长(天)'] = line.split(':')[1]

        exe_path = f'/proc/{pid}/exe'
        if os.path.exists(exe_path):
            output = subprocess.run(['readlink', exe_path], capture_output=True, text=True)

            if output.returncode == 0:
                ver_data['可执行文件路径'] = output.stdout.strip()

                output = subprocess.run([output.stdout.strip(), '--version'], capture_output=True, text=True, timeout=5)

                if output.returncode == 0:
                    ver_data['版本字符串'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取Redis版本信息失败: {e}')

    return ver_data
