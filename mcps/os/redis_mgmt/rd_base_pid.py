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
def fetch_user_group_info(pid):
    """
    获取用户/组信息
    """
    user_info = {}

    try:
        if os.path.exists(f'/proc/{pid}/status'):
            with open(f'/proc/{pid}/status', 'r') as f:
                status_lines = f.readlines()

            for line in status_lines:
                if line.startswith('Uid:'):
                    uid_parts = line.split()
                    if len(uid_parts) >= 2:
                        real_uid = uid_parts[1]
                        effective_uid = uid_parts[2]
                        user_info['用户ID(真实)'] = real_uid
                        user_info['用户ID(有效)'] = effective_uid

                        try:
                            user = pwd.getpwuid(int(real_uid))
                            user_info['用户名'] = user.pw_name
                            user_info['用户主目录'] = user.pw_dir
                            user_info['用户Shell'] = user.pw_shell
                        except Exception:
                            pass

                elif line.startswith('Gid:'):
                    gid_parts = line.split()
                    if len(gid_parts) >= 2:
                        real_gid = gid_parts[1]
                        effective_gid = gid_parts[2]
                        user_info['组ID(真实)'] = real_gid
                        user_info['组ID(有效)'] = effective_gid

                        try:
                            group = grp.getgrgid(int(real_gid))
                            user_info['组名'] = group.gr_name
                        except Exception:
                            pass

                elif line.startswith('Groups:'):
                    groups = line.split()[1:]
                    user_info['附加组'] = ', '.join(groups)

                    group_names = []
                    for gid in groups:
                        try:
                            group = grp.getgrgid(int(gid))
                            group_names.append(group.gr_name)
                        except Exception:
                            pass
                    if group_names:
                        user_info['附加组名'] = ', '.join(group_names)

        output = subprocess.run(['ps', '-p', pid, '-o', 'user,group'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    user_info['运行用户'] = parts[0]
                    user_info['运行组'] = parts[1]

        if os.path.exists(f'/proc/{pid}'):
            stat_path = f'/proc/{pid}/stat'
            if os.path.exists(stat_path):
                with open(stat_path, 'r') as f:
                    stat_data = f.read().split()

                if len(stat_data) > 8:
                    uid = stat_data[8]
                    user_info['文件系统用户ID'] = uid

        output = subprocess.run(['id'], capture_output=True, text=True)

        if output.returncode == 0:
            user_info['当前用户信息'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取用户/组信息失败: {e}')

    return user_info
