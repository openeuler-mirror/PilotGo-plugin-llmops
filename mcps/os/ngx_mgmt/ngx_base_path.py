import logging
import os
import platform
import re
import subprocess

from .utils import (

    check_nginx_installation, get_basic_paths, get_system_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_path')

def fetch_nginx_base_path():
    """
    获取Nginx安装路径、配置根路径、二进制/模块/日志默认路径的MCP工具

    返回:
        格式化的Nginx路径信息字符串，包含：
        - 安装路径和二进制文件位置
        - 配置根路径和配置文件
        - 模块路径（内置和动态）
        - 日志文件路径
        - PID文件路径
        - 默认网站根目录
        - 临时文件路径
        - 错误处理和状态检查
    """
    try:
        output = []
        output.append('=== Nginx路径信息 ===')

        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('======================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")

        # 获取基本路径信息
        basic_paths = get_basic_paths()
        output.append(f"\n=== 基本路径 ===")
        output.append(f"安装目录: {basic_paths['install_dir']}")
        output.append(f"二进制文件: {basic_paths['binary_path']}")
        output.append(f"启动脚本: {basic_paths['init_script']}")

        # 获取配置路径
        config_paths = fetch_config_paths()
        output.append(f"\n=== 配置路径 ===")
        output.append(f"配置根目录: {config_paths['config_root']}")
        output.append(f"主配置文件: {config_paths['main_config']}")
        output.append(f"虚拟主机目录: {config_paths['vhosts_dir']}")
        output.append(f"配置片段目录: {config_paths['conf_d_dir']}")

        # 获取模块路径
        module_paths = fetch_module_paths()
        output.append(f"\n=== 模块路径 ===")
        output.append(f"内置模块: {module_paths['builtin_modules']}")
        output.append(f"动态模块目录: {module_paths['dynamic_modules_dir']}")
        if module_paths['available_modules']:
            output.append(f"可用动态模块:")
            for module in module_paths['available_modules'][:5]:  # 显示前5个
                output.append(f"  - {module}")
            if len(module_paths['available_modules']) > 5:
                output.append(f"  ... 还有 {len(module_paths['available_modules']) - 5} 个模块 ...")

        # 获取日志路径
        log_paths = fetch_log_paths()
        output.append(f"\n=== 日志路径 ===")
        output.append(f"访问日志: {log_paths['access_log']}")
        output.append(f"错误日志: {log_paths['error_log']}")
        output.append(f"日志目录: {log_paths['log_dir']}")

        # 获取运行时路径
        runtime_paths = fetch_runtime_paths()
        output.append(f"\n=== 运行时路径 ===")
        output.append(f"PID文件: {runtime_paths['pid_file']}")
        output.append(f"锁文件: {runtime_paths['lock_file']}")

        # 获取网站内容路径
        content_paths = fetch_content_paths()
        output.append(f"\n=== 网站内容路径 ===")
        output.append(f"默认网站根目录: {content_paths['default_root']}")
        output.append(f"HTML目录: {content_paths['html_dir']}")

        # 获取临时文件路径
        temp_paths = fetch_temp_paths()
        output.append(f"\n=== 临时文件路径 ===")
        output.append(f"客户端临时文件: {temp_paths['client_temp']}")
        output.append(f"代理临时文件: {temp_paths['proxy_temp']}")
        output.append(f"FastCGI临时文件: {temp_paths['fastcgi_temp']}")
        output.append(f"临时文件目录: {temp_paths['temp_dir']}")

        # 获取系统特定路径
        system_paths = fetch_system_specific_paths()
        if system_paths['package_manager']:
            output.append(f"\n=== 系统特定路径 ===")
            output.append(f"包管理器: {system_paths['package_manager']}")
            output.append(f"服务配置: {system_paths['service_config']}")
            output.append(f"系统日志: {system_paths['system_log']}")

        # 路径有效性检查
        output.append(f"\n=== 路径状态检查 ===")
        path_status = verify_path_validity(basic_paths, config_paths, log_paths, runtime_paths)
        for status in path_status:
            output.append(status)

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx路径信息失败: {e}')
        return f'获取Nginx路径信息失败: {e}'