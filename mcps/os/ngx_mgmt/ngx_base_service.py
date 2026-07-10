import logging
import os
import platform
import re
import subprocess

from .utils import check_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_service')

def fetch_nginx_base_service():
    """
    获取Nginx系统服务状态（开机自启/手动）、服务管理路径的MCP工具

    返回:
        格式化的Nginx服务信息字符串，包含：
        - 服务安装状态
        - 服务运行状态
        - 开机自启状态
        - 服务管理路径
        - 服务配置文件路径
        - 服务启动方式（systemd/sysvinit/upstart）
        - 服务日志路径
        - 服务控制命令
    """
    try:
        output = []
        output.append('=== Nginx服务信息 ===')

        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('======================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")

        # 获取服务管理信息
        service_info = fetch_nginx_service_info()

        # 服务状态
        output.append(f"\n=== 服务运行状态 ===")
        output.append(f"服务状态: {service_info.get('status', 'Unknown')}")
        output.append(f"主进程PID: {service_info.get('pid', 'Unknown')}")
        output.append(f"启动时间: {service_info.get('start_time', 'Unknown')}")
        output.append(f"描述: {service_info.get('description', 'Unknown')}")

        # 开机自启状态
        output.append(f"\n=== 开机自启状态 ===")
        output.append(f"启用状态: {'已启用' if service_info.get('enabled', False) else '未启用'}")
        output.append(f"开机自启: {'是' if service_info.get('enabled_boot', False) else '否'}")
        output.append(f"启动方式: {service_info.get('init_system', 'Unknown')}")

        # 服务管理路径
        output.append(f"\n=== 服务管理路径 ===")
        output.append(f"服务单元文件: {service_info.get('service_file', 'Unknown')}")
        output.append(f"服务配置目录: {service_info.get('service_config_dir', 'Unknown')}")
        output.append(f"PID文件: {service_info.get('pid_file', 'Unknown')}")
        output.append(f"锁文件: {service_info.get('lock_file', 'Unknown')}")

        # 服务控制命令
        output.append(f"\n=== 服务控制命令 ===")
        control_commands = service_info.get('control_commands', {})
        output.append(f"启动命令: {control_commands.get('start', 'Unknown')}")
        output.append(f"停止命令: {control_commands.get('stop', 'Unknown')}")
        output.append(f"重启命令: {control_commands.get('restart', 'Unknown')}")
        output.append(f"重载命令: {control_commands.get('reload', 'Unknown')}")
        output.append(f"状态命令: {control_commands.get('status', 'Unknown')}")

        # 服务日志路径
        output.append(f"\n=== 服务日志路径 ===")
        log_paths = service_info.get('log_paths', {})
        output.append(f"系统日志: {log_paths.get('system_log', 'Unknown')}")
        output.append(f"服务日志: {log_paths.get('service_log', 'Unknown')}")
        output.append(f"错误日志: {log_paths.get('error_log', 'Unknown')}")

        # 服务状态检查
        output.append(f"\n=== 服务状态检查 ===")
        status_checks = verify_service_status()
        for check in status_checks:
            output.append(f"  {check}")

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx服务信息失败: {e}')
        return f'获取Nginx服务信息失败: {e}'

def fetch_nginx_service_info():
    """
    获取Nginx服务详细信息

    返回:
        dict: 服务信息字典
    """
    try:
        service_info = {
            'status': 'Unknown',
            'enabled': False,
            'enabled_boot': False,
            'description': 'Unknown',
            'pid': 'Unknown',
            'start_time': 'Unknown',
            'service_file': 'Unknown',
            'service_config_dir': 'Unknown',
            'pid_file': 'Unknown',
            'lock_file': 'Unknown',
            'init_system': 'Unknown',
            'control_commands': {},
            'log_paths': {}
        }

        # 检测初始化系统类型
        init_system = spot_init_system()
        service_info['init_system'] = init_system

        if init_system == 'systemd':
            service_info.update(fetch_systemd_service_info())
        elif init_system == 'sysvinit':
            service_info.update(fetch_sysvinit_service_info())
        elif init_system == 'upstart':
            service_info.update(fetch_upstart_service_info())
        else:
            service_info.update(fetch_generic_service_info())

        return service_info

    except Exception as e:
        logger.error(f'获取Nginx服务信息失败: {e}')
        return service_info

def spot_init_system():
    """
    检测系统初始化系统类型

    返回:
        str: 初始化系统类型
    """
    try:
        # 检查systemd
        if os.path.exists('/run/systemd/system'):
            return 'systemd'

        # 检查systemctl命令
        output = subprocess.run(['which', 'systemctl'], capture_output=True, text=True)
        if output.returncode == 0:
            return 'systemd'

        # 检查upstart
        if os.path.exists('/sbin/upstart') or os.path.exists('/etc/init'):
            return 'upstart'

        # 检查sysvinit
        if os.path.exists('/etc/init.d'):
            return 'sysvinit'

        return 'unknown'

    except Exception:
        return 'unknown'

def fetch_systemd_service_info():
    """
    获取systemd服务信息

    返回:
        dict: systemd服务信息
    """
    try:
        service_info = {}

        # 获取服务状态
        status_result = subprocess.run(['systemctl', 'status', 'nginx'], capture_output=True, text=True)
        if status_result.returncode == 0:
            output = status_result.stdout
            service_info['status'] = '运行中'

            # 解析详细信息
            for line in output.split('\n'):
                if 'Active:' in line:
                    status_match = re.search(r'Active:\s*(\w+)', line)  # NOSONAR
                    if status_match:
                        service_info['status'] = status_match.group(1)
                elif 'Description:' in line:
                    service_info['description'] = line.split(':', 1)[1].strip()
                elif 'Main PID:' in line:
                    pid_match = re.search(r'Main PID:\s*(\d+)', line)  # NOSONAR
                    if pid_match:
                        service_info['pid'] = pid_match.group(1)
                elif 'Started' in line:
                    service_info['start_time'] = line.strip()
        else:
            service_info['status'] = '未运行'

        # 检查启用状态
        enable_result = subprocess.run(['systemctl', 'is-enabled', 'nginx'], capture_output=True, text=True)
        if enable_result.returncode == 0:
            service_info['enabled'] = True
            service_info['enabled_boot'] = True

        # 获取服务文件路径
        show_result = subprocess.run(['systemctl', 'show', 'nginx', '--property=FragmentPath'], capture_output=True, text=True)
        if show_result.returncode == 0:
            path_match = re.search(r'FragmentPath=(.+)', show_result.stdout.strip())  # NOSONAR
            if path_match:
                service_info['service_file'] = path_match.group(1)
                service_info['service_config_dir'] = os.path.dirname(path_match.group(1))

        # 控制命令
        service_info['control_commands'] = {
            'start': 'systemctl start nginx',
            'stop': 'systemctl stop nginx',
            'restart': 'systemctl restart nginx',
            'reload': 'systemctl reload nginx',
            'status': 'systemctl status nginx'
        }

        # 日志路径
        service_info['log_paths'] = {
            'system_log': 'journalctl -u nginx',
            'service_log': '/var/log/nginx/access.log',
            'error_log': '/var/log/nginx/error.log'
        }

        # PID文件
        service_info['pid_file'] = '/run/nginx.pid'
        service_info['lock_file'] = '/run/nginx.lock'

        return service_info

    except Exception as e:
        logger.error(f'获取systemd服务信息失败: {e}')
        return {}

def fetch_sysvinit_service_info():
    """
    获取sysvinit服务信息

    返回:
        dict: sysvinit服务信息
    """
    try:
        service_info = {}

        # 检查服务脚本是否存在
        service_script = '/etc/init.d/nginx'
        if os.path.exists(service_script):
            service_info['service_file'] = service_script

            # 获取服务状态
            status_result = subprocess.run([service_script, 'status'], capture_output=True, text=True)
            if status_result.returncode == 0:
                service_info['status'] = '运行中'
            else:
                service_info['status'] = '未运行'

            # 检查chkconfig
            chkconfig_result = subprocess.run(['chkconfig', '--list', 'nginx'], capture_output=True, text=True)
            if chkconfig_result.returncode == 0:
                service_info['enabled'] = True
                # 检查是否在运行级别3和5启用
                if '3:on' in chkconfig_result.stdout and '5:on' in chkconfig_result.stdout:
                    service_info['enabled_boot'] = True

        # 控制命令
        service_info['control_commands'] = {
            'start': '/etc/init.d/nginx start',
            'stop': '/etc/init.d/nginx stop',
            'restart': '/etc/init.d/nginx restart',
            'reload': '/etc/init.d/nginx reload',
            'status': '/etc/init.d/nginx status'
        }

        # 日志路径
        service_info['log_paths'] = {
            'system_log': '/var/log/messages',
            'service_log': '/var/log/nginx/access.log',
            'error_log': '/var/log/nginx/error.log'
        }

        # PID文件
        service_info['pid_file'] = '/var/run/nginx.pid'
        service_info['lock_file'] = '/var/lock/nginx.lock'

        return service_info

    except Exception as e:
        logger.error(f'获取sysvinit服务信息失败: {e}')
        return {}

def fetch_upstart_service_info():
    """
    获取upstart服务信息

    返回:
        dict: upstart服务信息
    """
    try:
        service_info = {}

        # 获取服务状态
        status_result = subprocess.run(['status', 'nginx'], capture_output=True, text=True)
        if status_result.returncode == 0:
            output = status_result.stdout.strip()
            if 'start/running' in output:
                service_info['status'] = '运行中'
                pid_match = re.search(r'process\s+(\d+)', output)  # NOSONAR
                if pid_match:
                    service_info['pid'] = pid_match.group(1)
            else:
                service_info['status'] = '未运行'

        # 检查配置文件
        config_files = [
            '/etc/init/nginx.conf',
            '/etc/init/nginx.conf.override'
        ]

        for config_file in config_files:
            if os.path.exists(config_file):
                service_info['service_file'] = config_file
                service_info['service_config_dir'] = '/etc/init'
                break

        # 控制命令
        service_info['control_commands'] = {
            'start': 'start nginx',
            'stop': 'stop nginx',
            'restart': 'restart nginx',
            'reload': 'reload nginx',
            'status': 'status nginx'
        }

        # 日志路径
        service_info['log_paths'] = {
            'system_log': '/var/log/syslog',
            'service_log': '/var/log/nginx/access.log',
            'error_log': '/var/log/nginx/error.log'
        }

        return service_info

    except Exception as e:
        logger.error(f'获取upstart服务信息失败: {e}')
        return {}