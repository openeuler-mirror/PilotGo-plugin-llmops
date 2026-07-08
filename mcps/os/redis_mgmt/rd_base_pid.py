from datetime import datetime
import logging
import os
import subprocess
import time

from .rd_shared import *
import grp
import pwd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('redis_base_pid')

def fetch_redis_base_pid(pid_type=None):
    """
    采集Redis主进程PID、进程归属用户/组、进程启动时间、运行时长

    参数:
        pid_type: 指定要采集的进程信息类型，可选值：
                  - "pid": 仅采集进程ID信息
                  - "user": 仅采集用户/组信息
                  - "time": 仅采集时间信息（启动时间/运行时长）
                  - "status": 仅采集进程状态信息
                  - "all": 采集所有进程信息（默认）

    返回:
        格式化的Redis进程信息字符串
    """
    try:
        output = []
        output.append('=== Redis进程信息 ===')

        rd_pids = find_all_redis_pids()

        if not rd_pids:
            output.append('未检测到运行中的Redis进程')
            output.append('请确认Redis服务是否已启动')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'检测到 {len(rd_pids)} 个Redis进程')

        for i, pid in enumerate(rd_pids, 1):
            output.append(f'\n--- 进程 {i} (PID: {pid}) ---')

            if pid_type is None or pid_type == "all" or pid_type == "pid":
                pid_info = fetch_pid_info(pid)
                if pid_info:
                    output.append('\n进程ID信息:')
                    for key, value in pid_info.items():
                        output.append(f"  {key}: {value}")

            if pid_type is None or pid_type == "all" or pid_type == "user":
                user_info = fetch_user_group_info(pid)
                if user_info:
                    output.append('\n用户/组信息:')
                    for key, value in user_info.items():
                        output.append(f"  {key}: {value}")

            if pid_type is None or pid_type == "all" or pid_type == "time":
                time_info = fetch_time_info(pid)
                if time_info:
                    output.append('\n时间信息:')
                    for key, value in time_info.items():
                        output.append(f"  {key}: {value}")

            if pid_type is None or pid_type == "all" or pid_type == "status":
                status_info = fetch_status_info(pid)
                if status_info:
                    output.append('\n进程状态:')
                    for key, value in status_info.items():
                        output.append(f"  {key}: {value}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis进程信息失败: {e}')
        return f'获取Redis进程信息失败: {e}'
def fetch_pid_info(pid):
    """
    获取进程ID信息
    """
    pid_info = {}

    try:
        pid_info['进程ID'] = pid

        if os.path.exists(f'/proc/{pid}'):
            exe_path = f'/proc/{pid}/exe'
            if os.path.exists(exe_path):
                output = subprocess.run(['readlink', '-f', exe_path], capture_output=True, text=True)

                if output.returncode == 0:
                    pid_info['可执行文件'] = output.stdout.strip()

            cmdline_path = f'/proc/{pid}/cmdline'
            if os.path.exists(cmdline_path):
                with open(cmdline_path, 'r') as f:
                    cmdline = f.read().replace('\x00', ' ')
                pid_info['命令行'] = cmdline

            cwd_path = f'/proc/{pid}/cwd'
            if os.path.exists(cwd_path):
                output = subprocess.run(['readlink', '-f', cwd_path], capture_output=True, text=True)

                if output.returncode == 0:
                    pid_info['工作目录'] = output.stdout.strip()

            output = subprocess.run(['ps', '-p', pid, '-o', 'pid,ppid,pgid,sid,tty'], capture_output=True, text=True)

            if output.returncode == 0:
                lines = output.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        pid_info['父进程ID'] = parts[1]
                        pid_info['进程组ID'] = parts[2]
                        pid_info['会话ID'] = parts[3]
                        pid_info['终端'] = parts[4]

            output = subprocess.run(['redis-cli', 'INFO', 'server'], capture_output=True, text=True, timeout=5)

            if output.returncode == 0:
                info_lines = output.stdout.split('\n')
                for line in info_lines:
                    if line.startswith('process_id:'):
                        redis_pid = line.split(':')[1]
                        if redis_pid == pid:
                            pid_info['Redis进程ID'] = redis_pid
                    elif line.startswith('run_id:'):
                        pid_info['运行ID'] = line.split(':')[1]

        output = subprocess.run(['ps', '-p', pid, '-o', 'comm='], capture_output=True, text=True)

        if output.returncode == 0:
            pid_info['进程名称'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取进程ID信息失败: {e}')

    return pid_info
