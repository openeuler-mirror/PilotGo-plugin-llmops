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