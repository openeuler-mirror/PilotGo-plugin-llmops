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
def fetch_time_info(pid):
    """
    获取时间信息（启动时间/运行时长）
    """
    time_info = {}

    try:
        if os.path.exists(f'/proc/{pid}/stat'):
            with open(f'/proc/{pid}/stat', 'r') as f:
                stat_data = f.read().split()

            if len(stat_data) > 21:
                starttime_ticks = int(stat_data[21])

                try:
                    output = subprocess.run(['getconf', 'CLK_TCK'], capture_output=True, text=True)

                    if output.returncode == 0:
                        hz = int(output.stdout.strip())
                        starttime_seconds = starttime_ticks / hz

                        boot_time_result = subprocess.run(['cat', '/proc/stat'], capture_output=True, text=True)

                        if boot_time_result.returncode == 0:
                            for line in boot_time_result.stdout.split('\n'):
                                if line.startswith('btime'):
                                    btime = float(line.split()[1])
                                    start_timestamp = btime + starttime_seconds
                                    start_datetime = datetime.fromtimestamp(start_timestamp)

                                    time_info['启动时间'] = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
                                    time_info['启动时间戳'] = str(start_timestamp)

                                    current_time = time.time()
                                    uptime_seconds = current_time - start_timestamp
                                    uptime_days = int(uptime_seconds // 86400)
                                    uptime_hours = int((uptime_seconds % 86400) // 3600)
                                    uptime_minutes = int((uptime_seconds % 3600) // 60)
                                    uptime_secs = int(uptime_seconds % 60)

                                    if uptime_days > 0:
                                        time_info['运行时长'] = f"{uptime_days}天 {uptime_hours}小时 {uptime_minutes}分钟"
                                    elif uptime_hours > 0:
                                        time_info['运行时长'] = f"{uptime_hours}小时 {uptime_minutes}分钟"
                                    elif uptime_minutes > 0:
                                        time_info['运行时长'] = f"{uptime_minutes}分钟 {uptime_secs}秒"
                                    else:
                                        time_info['运行时长'] = f"{uptime_secs}秒"

                                    time_info['运行时长(秒)'] = f"{uptime_seconds:.2f}"
                                    break
                except Exception as e:
                    logger.error(f'计算启动时间失败: {e}')

        output = subprocess.run(['ps', '-p', pid, '-o', 'lstart,etime'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split(None, 1)
                if len(parts) >= 2:
                    time_info['进程启动时间'] = parts[0]
                    time_info['进程运行时长'] = parts[1]

        output = subprocess.run(['redis-cli', 'INFO', 'server'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('uptime_in_seconds:'):
                    uptime_seconds = int(line.split(':')[1])
                    uptime_days = uptime_seconds // 86400
                    uptime_hours = (uptime_seconds % 86400) // 3600
                    uptime_minutes = (uptime_seconds % 3600) // 60

                    if uptime_days > 0:
                        time_info['Redis运行时长'] = f"{uptime_days}天 {uptime_hours}小时 {uptime_minutes}分钟"
                    elif uptime_hours > 0:
                        time_info['Redis运行时长'] = f"{uptime_hours}小时 {uptime_minutes}分钟"
                    else:
                        time_info['Redis运行时长'] = f"{uptime_minutes}分钟"

                    time_info['Redis运行时长(秒)'] = str(uptime_seconds)

                elif line.startswith('uptime_in_days:'):
                    time_info['Redis运行天数'] = line.split(':')[1]

        if os.path.exists(f'/proc/{pid}'):
            stat_path = f'/proc/{pid}/stat'
            if os.path.exists(stat_path):
                with open(stat_path, 'r') as f:
                    stat_data = f.read().split()

                if len(stat_data) > 13:
                    utime = int(stat_data[13])
                    stime = int(stat_data[14])
                    total_cpu_time = utime + stime
                    time_info['CPU时间(总计)'] = f"{total_cpu_time} jiffies"
                    time_info['CPU时间(用户态)'] = f"{utime} jiffies"
                    time_info['CPU时间(内核态)'] = f"{stime} jiffies"

    except Exception as e:
        logger.error(f'获取时间信息失败: {e}')

    return time_info
def fetch_status_info(pid):
    """
    获取进程状态信息
    """
    status_info = {}

    try:
        if os.path.exists(f'/proc/{pid}/status'):
            with open(f'/proc/{pid}/status', 'r') as f:
                status_lines = f.readlines()

            for line in status_lines:
                if line.startswith('Name:'):
                    status_info['进程名'] = line.split(':')[1].strip()
                elif line.startswith('State:'):
                    status_info['进程状态'] = line.split(':')[1].strip()
                elif line.startswith('Threads:'):
                    status_info['线程数'] = line.split(':')[1].strip()
                elif line.startswith('VmPeak:'):
                    status_info['虚拟内存峰值'] = line.split(':')[1].strip()
                elif line.startswith('VmSize:'):
                    status_info['虚拟内存大小'] = line.split(':')[1].strip()
                elif line.startswith('VmRSS:'):
                    status_info['物理内存使用'] = line.split(':')[1].strip()
                elif line.startswith('VmData:'):
                    status_info['数据段大小'] = line.split(':')[1].strip()
                elif line.startswith('VmStk:'):
                    status_info['栈大小'] = line.split(':')[1].strip()
                elif line.startswith('VmExe:'):
                    status_info['代码段大小'] = line.split(':')[1].strip()
                elif line.startswith('VmLib:'):
                    status_info['库大小'] = line.split(':')[1].strip()
                elif line.startswith('SigQ:'):
                    status_info['信号队列'] = line.split(':')[1].strip()
                elif line.startswith('SigPnd:'):
                    status_info['挂起信号'] = line.split(':')[1].strip()
                elif line.startswith('ShdPnd:'):
                    status_info['共享挂起信号'] = line.split(':')[1].strip()
                elif line.startswith('CapInh:'):
                    status_info['继承能力'] = line.split(':')[1].strip()
                elif line.startswith('CapPrm:'):
                    status_info['允许能力'] = line.split(':')[1].strip()
                elif line.startswith('CapEff:'):
                    status_info['有效能力'] = line.split(':')[1].strip()

        if os.path.exists(f'/proc/{pid}/stat'):
            with open(f'/proc/{pid}/stat', 'r') as f:
                stat_data = f.read().split()

            if len(stat_data) > 2:
                state = stat_data[2]
                state_map = {
                    'R': '运行中',
                    'S': '可中断睡眠',
                    'D': '不可中断睡眠',
                    'T': '已停止',
                    't': '跟踪中',
                    'Z': '僵尸进程',
                    'X': '已死亡',
                    'x': '已死亡',
                    'K': '已杀死',
                    'W': '换页中',
                    'P': '换页中'
                }
                status_info['进程状态(原始)'] = state
                status_info['进程状态(描述)'] = state_map.get(state, '未知')

        output = subprocess.run(['ps', '-p', pid, '-o', 'state,s'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    status_info['PS状态'] = parts[0]
                    status_info['PS状态描述'] = parts[1]

        output = subprocess.run(['top', '-b', '-n', '1', '-p', pid], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for line in lines:
                if pid in line and 'redis-server' in line:
                    parts = line.split()
                    if len(parts) >= 12:
                        status_info['CPU使用率'] = f"{parts[8]}%"
                        status_info['内存使用率'] = parts[9]
                    break

        output = subprocess.run(['redis-cli', 'INFO', 'server'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('redis_version:'):
                    status_info['Redis版本'] = line.split(':')[1]
                elif line.startswith('tcp_port:'):
                    status_info['监听端口'] = line.split(':')[1]
                elif line.startswith('mode:'):
                    status_info['运行模式'] = line.split(':')[1]

        output = subprocess.run(['redis-cli', 'PING'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            status_info['Redis响应'] = output.stdout.strip()
            status_info['Redis状态'] = '正常'
        else:
            status_info['Redis状态'] = '异常'

    except Exception as e:
        logger.error(f'获取进程状态信息失败: {e}')

    return status_info

TOOL_CONFIG = {
    "name": "fetch_redis_base_pid",
    "function": fetch_redis_base_pid,
    "description": "采集Redis主进程PID、进程归属用户/组、进程启动时间、运行时长",
    "parameters": {
        "type": "object",
        "properties": {
            "pid_type": {
                "type": "string",
                "description": "指定要采集的进程信息类型，可选值：pid（进程ID信息）、user（用户/组信息）、time（时间信息）、status（进程状态信息）、all（所有进程信息）",
                "enum": ["pid", "user", "time", "status", "all"]
            }
        },
        "required": []
    }
}
