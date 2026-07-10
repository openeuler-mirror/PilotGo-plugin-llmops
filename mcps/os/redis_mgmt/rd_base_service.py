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
def fetch_autostart_status():
    """
    获取开机自启状态
    """
    autostart_info = {}

    try:
        service_names = ['redis.service', 'redis-server.service', 'redis']

        for service_name in service_names:
            output = subprocess.run(['systemctl', 'is-enabled', service_name], capture_output=True, text=True)

            if output.returncode == 0:
                autostart_info['Systemd自启状态'] = '启用'
                autostart_info['Systemd服务名称'] = service_name
                break
            elif output.returncode == 1:
                autostart_info['Systemd自启状态'] = '禁用'
                autostart_info['Systemd服务名称'] = service_name
                break

        output = subprocess.run(
            ['systemctl', 'list-unit-files', '|', 'grep', '-i', 'redis'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            redis_units = output.stdout.strip().split('\n')
            autostart_info['Redis服务单元'] = f"{len(redis_units)} 个"
            for unit in redis_units:
                if 'enabled' in unit:
                    autostart_info['已启用单元'] = unit.strip()

        output = subprocess.run(
            ['chkconfig', '--list', '|', 'grep', '-i', 'redis'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            autostart_info['SysV自启状态'] = output.stdout.strip()

        output = subprocess.run(
            ['ls', '/etc/rc*.d/', '|', 'grep', '-i', 'redis'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            autostart_info['启动脚本'] = output.stdout.strip()

        output = subprocess.run(['update-rc.d', '-n', 'redis', 'defaults', '2>&1'], capture_output=True, text=True)

        if output.returncode == 0 or 'already exists' in output.stderr:
            autostart_info['Update-rc.d状态'] = '已配置'

        output = subprocess.run(['systemctl', 'get-default'], capture_output=True, text=True)

        if output.returncode == 0:
            autostart_info['系统默认运行级别'] = output.stdout.strip()

        output = subprocess.run(['runlevel'], capture_output=True, text=True)

        if output.returncode == 0:
            autostart_info['当前运行级别'] = output.stdout.strip()

        output = subprocess.run(['systemctl', 'is-system-running'], capture_output=True, text=True)

        if output.returncode == 0:
            autostart_info['系统运行状态'] = output.stdout.strip()

        output = subprocess.run(['systemd-analyze', 'blame', '|', 'grep', '-i', 'redis'], capture_output=True, text=True)

        if output.returncode == 0 and output.stdout.strip():
            autostart_info['启动耗时'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取开机自启状态失败: {e}')

    return autostart_info
def fetch_service_script():
    """
    获取服务管理脚本路径
    """
    script_info = {}

    try:
        output = subprocess.run(['systemctl', 'cat', 'redis.service'], capture_output=True, text=True)

        if output.returncode == 0:
            script_info['Systemd服务文件'] = '已找到'

            for line in output.stdout.split('\n'):
                if line.startswith('Description='):
                    script_info['服务描述'] = line.split('=', 1)[1]
                elif line.startswith('ExecStart='):
                    script_info['启动命令'] = line.split('=', 1)[1]
                elif line.startswith('ExecStop='):
                    script_info['停止命令'] = line.split('=', 1)[1]
                elif line.startswith('ExecReload='):
                    script_info['重载命令'] = line.split('=', 1)[1]
                elif line.startswith('PIDFile='):
                    script_info['PID文件'] = line.split('=', 1)[1]

        output = subprocess.run(['systemctl', 'cat', 'redis-server.service'], capture_output=True, text=True)

        if output.returncode == 0:
            script_info['Redis-Server服务文件'] = '已找到'

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'FragmentPath'], capture_output=True, text=True)

        if output.returncode == 0:
            fragment_path = output.stdout.strip()
            if fragment_path:
                script_info['服务文件路径'] = fragment_path

        output = subprocess.run(['systemctl', 'show', 'redis-server.service', '-p', 'FragmentPath'], capture_output=True, text=True)

        if output.returncode == 0:
            fragment_path = output.stdout.strip()
            if fragment_path:
                script_info['Redis-Server文件路径'] = fragment_path

        common_init_paths = [
            '/etc/init.d/redis',
            '/etc/init.d/redis-server',
            '/etc/rc.d/init.d/redis',
            '/etc/rc.d/init.d/redis-server'
        ]

        for init_path in common_init_paths:
            if os.path.exists(init_path):
                script_info['SysV初始化脚本'] = init_path
                script_info['SysV脚本状态'] = '存在'
                break

        output = subprocess.run(['which', 'redis-server'], capture_output=True, text=True)

        if output.returncode == 0:
            script_info['Redis可执行文件'] = output.stdout.strip()

        output = subprocess.run(['which', 'redis-cli'], capture_output=True, text=True)

        if output.returncode == 0:
            script_info['Redis CLI工具'] = output.stdout.strip()

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecStart'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_start = output.stdout.strip()
            if exec_start:
                script_info['ExecStart配置'] = exec_start

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecStartPre'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_start_pre = output.stdout.strip()
            if exec_start_pre:
                script_info['ExecStartPre配置'] = exec_start_pre

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecStartPost'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_start_post = output.stdout.strip()
            if exec_start_post:
                script_info['ExecStartPost配置'] = exec_start_post

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecStop'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_stop = output.stdout.strip()
            if exec_stop:
                script_info['ExecStop配置'] = exec_stop

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecStopPost'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_stop_post = output.stdout.strip()
            if exec_stop_post:
                script_info['ExecStopPost配置'] = exec_stop_post

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'ExecReload'], capture_output=True, text=True)

        if output.returncode == 0:
            exec_reload = output.stdout.strip()
            if exec_reload:
                script_info['ExecReload配置'] = exec_reload

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'Restart'], capture_output=True, text=True)

        if output.returncode == 0:
            restart = output.stdout.strip()
            if restart:
                script_info['重启配置'] = restart

    except Exception as e:
        logger.error(f'获取服务管理脚本路径失败: {e}')

    return script_info
def fetch_restart_policy():
    """
    获取重启策略
    """
    restart_info = {}

    try:
        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'Restart'], capture_output=True, text=True)

        if output.returncode == 0:
            restart = output.stdout.strip()
            if restart:
                restart_info['重启策略'] = restart
                restart_map = {
                    'no': '不重启',
                    'on-success': '成功时重启',
                    'on-failure': '失败时重启',
                    'on-abnormal': '异常时重启',
                    'on-watchdog': '看门狗触发时重启',
                    'always': '总是重启'
                }
                restart_info['重启策略说明'] = restart_map.get(restart, '未知')

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'RestartSec'], capture_output=True, text=True)

        if output.returncode == 0:
            restart_sec = output.stdout.strip()
            if restart_sec and restart_sec != '0':
                restart_info['重启间隔'] = f"{restart_sec} 秒"

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'RestartMode'], capture_output=True, text=True)

        if output.returncode == 0:
            restart_mode = output.stdout.strip()
            if restart_mode:
                restart_info['重启模式'] = restart_mode

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'StartLimitIntervalSec'], capture_output=True, text=True)

        if output.returncode == 0:
            start_limit = output.stdout.strip()
            if start_limit and start_limit != '0' and start_limit != 'infinity':
                restart_info['启动限制间隔'] = f"{start_limit} 秒"

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'StartLimitBurst'], capture_output=True, text=True)

        if output.returncode == 0:
            start_burst = output.stdout.strip()
            if start_burst and start_burst != '0':
                restart_info['启动限制次数'] = start_burst

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'TimeoutStartSec'], capture_output=True, text=True)

        if output.returncode == 0:
            timeout_start = output.stdout.strip()
            if timeout_start:
                restart_info['启动超时'] = f"{timeout_start} 秒"

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'TimeoutStopSec'], capture_output=True, text=True)

        if output.returncode == 0:
            timeout_stop = output.stdout.strip()
            if timeout_stop:
                restart_info['停止超时'] = f"{timeout_stop} 秒"

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'TimeoutSec'], capture_output=True, text=True)

        if output.returncode == 0:
            deadline = output.stdout.strip()
            if deadline:
                restart_info['通用超时'] = f"{deadline} 秒"

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'KillMode'], capture_output=True, text=True)

        if output.returncode == 0:
            kill_mode = output.stdout.strip()
            if kill_mode:
                restart_info['终止模式'] = kill_mode
                kill_mode_map = {
                    'control-group': '终止控制组内所有进程',
                    'process': '仅终止主进程',
                    'mixed': '终止主进程和控制组内所有进程',
                    'none': '不终止任何进程'
                }
                restart_info['终止模式说明'] = kill_mode_map.get(kill_mode, '未知')

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'KillSignal'], capture_output=True, text=True)

        if output.returncode == 0:
            kill_signal = output.stdout.strip()
            if kill_signal:
                restart_info['终止信号'] = kill_signal

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'SendSIGKILL'], capture_output=True, text=True)

        if output.returncode == 0:
            send_sigkill = output.stdout.strip()
            if send_sigkill:
                restart_info['发送SIGKILL'] = '是' if send_sigkill == 'yes' else '否'

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'RemainAfterExit'], capture_output=True, text=True)

        if output.returncode == 0:
            remain_after_exit = output.stdout.strip()
            if remain_after_exit:
                restart_info['退出后保持激活'] = '是' if remain_after_exit == 'yes' else '否'

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'WantedBy'], capture_output=True, text=True)

        if output.returncode == 0:
            wanted_by = output.stdout.strip()
            if wanted_by:
                restart_info['依赖目标'] = wanted_by

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'Requires'], capture_output=True, text=True)

        if output.returncode == 0:
            requires = output.stdout.strip()
            if requires:
                restart_info['依赖服务'] = requires

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'After'], capture_output=True, text=True)

        if output.returncode == 0:
            after = output.stdout.strip()
            if after:
                restart_info['启动顺序'] = after

        output = subprocess.run(['systemctl', 'show', 'redis.service', '-p', 'Before'], capture_output=True, text=True)

        if output.returncode == 0:
            before = output.stdout.strip()
            if before:
                restart_info['前置服务'] = before

    except Exception as e:
        logger.error(f'获取重启策略失败: {e}')

    return restart_info

TOOL_CONFIG = {
    "name": "fetch_redis_base_service",
    "function": fetch_redis_base_service,
    "description": "采集Redis系统服务状态（开机自启/手动）、服务管理脚本路径、重启策略",
    "parameters": {
        "type": "object",
        "properties": {
            "service_type": {
                "type": "string",
                "description": "指定要采集的服务信息类型，可选值：status（服务状态）、autostart（开机自启状态）、script（服务管理脚本路径）、restart（重启策略）、all（所有服务信息）",
                "enum": ["status", "autostart", "script", "restart", "all"]
            }
        },
        "required": []
    }
}
