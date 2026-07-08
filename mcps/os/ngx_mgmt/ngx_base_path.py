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

def fetch_config_paths():
    """获取配置路径信息"""
    try:
        cfg_state = {
            'config_root': 'Unknown',
            'main_config': 'Unknown',
            'vhosts_dir': 'Unknown',
            'conf_d_dir': 'Unknown'
        }

        # 常见配置路径
        common_config_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/usr/local/etc/nginx/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]

        # 检查nginx -t输出获取配置文件路径
        try:
            output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
            if output.returncode == 0 or output.returncode == 1:  # 0成功，1可能有配置错误但仍显示路径
                output = output.stdout.strip()
                # 从输出中提取配置文件路径
                config_match = re.search(r'file ([^\s]+) test', output)  # NOSONAR
                if config_match:
                    config_file = config_match.group(1)
                    cfg_state['main_config'] = config_file
                    cfg_state['config_root'] = os.path.dirname(config_file)
        except Exception:
            pass

        # 如果通过nginx -t没有获取到，检查常见路径
        if cfg_state['main_config'] == 'Unknown':
            for config_path in common_config_paths:
                if os.path.exists(config_path):
                    cfg_state['main_config'] = config_path
                    cfg_state['config_root'] = os.path.dirname(config_path)
                    break

        # 如果找到了配置根目录，检查子目录
        if cfg_state['config_root'] != 'Unknown':
            config_root = cfg_state['config_root']

            # 检查sites-enabled/sites-available (Debian/Ubuntu风格)
            if os.path.exists(os.path.join(config_root, 'sites-enabled')):
                cfg_state['vhosts_dir'] = os.path.join(config_root, 'sites-enabled')
            elif os.path.exists(os.path.join(config_root, 'conf.d')):
                cfg_state['vhosts_dir'] = os.path.join(config_root, 'conf.d')

            # 检查conf.d目录
            if os.path.exists(os.path.join(config_root, 'conf.d')):
                cfg_state['conf_d_dir'] = os.path.join(config_root, 'conf.d')

        return cfg_state

    except Exception as e:
        logger.error(f'获取配置路径信息失败: {e}')
        return {
            'config_root': '获取失败',
            'main_config': '获取失败',
            'vhosts_dir': '获取失败',
            'conf_d_dir': '获取失败'
        }

def fetch_module_paths():
    """获取模块路径信息"""
    try:
        mod_info = {
            'builtin_modules': '内置在nginx二进制中',
            'dynamic_modules_dir': 'Unknown',
            'available_modules': []
        }

        # 常见模块路径
        common_module_paths = [
            '/usr/lib/nginx/modules',
            '/usr/lib64/nginx/modules',
            '/usr/local/nginx/modules',
            '/etc/nginx/modules',
            '/usr/share/nginx/modules'
        ]

        # 查找动态模块目录
        for module_path in common_module_paths:
            if os.path.exists(module_path):
                mod_info['dynamic_modules_dir'] = module_path

                # 列出可用的动态模块
                try:
                    for item in os.listdir(module_path):
                        if item.endswith('.so'):
                            mod_info['available_modules'].append(item)
                except Exception:
                    pass
                break

        return mod_info

    except Exception as e:
        logger.error(f'获取模块路径信息失败: {e}')
        return {
            'builtin_modules': '获取失败',
            'dynamic_modules_dir': '获取失败',
            'available_modules': []
        }

def fetch_log_paths():
    """获取日志路径信息"""
    try:
        log_info = {
            'access_log': 'Unknown',
            'error_log': 'Unknown',
            'log_dir': 'Unknown'
        }

        # 常见日志路径
        common_log_paths = [
            '/var/log/nginx',
            '/usr/local/nginx/logs',
            '/var/log/httpd',
            '/var/log'
        ]

        # 查找日志目录
        for log_path in common_log_paths:
            if os.path.exists(log_path):
                log_info['log_dir'] = log_path

                # 检查具体的日志文件
                access_log_path = os.path.join(log_path, 'access.log')
                error_log_path = os.path.join(log_path, 'error.log')

                if os.path.exists(access_log_path):
                    log_info['access_log'] = access_log_path
                elif os.path.exists(os.path.join(log_path, 'access_log')):
                    log_info['access_log'] = os.path.join(log_path, 'access_log')

                if os.path.exists(error_log_path):
                    log_info['error_log'] = error_log_path
                elif os.path.exists(os.path.join(log_path, 'error_log')):
                    log_info['error_log'] = os.path.join(log_path, 'error_log')

                # 如果找到了日志文件，就使用这个目录
                if log_info['access_log'] != 'Unknown' or log_info['error_log'] != 'Unknown':
                    break

        return log_info

    except Exception as e:
        logger.error(f'获取日志路径信息失败: {e}')
        return {
            'access_log': '获取失败',
            'error_log': '获取失败',
            'log_dir': '获取失败'
        }

def fetch_runtime_paths():
    """获取运行时路径信息"""
    try:
        runtime_info = {
            'pid_file': 'Unknown',
            'lock_file': 'Unknown'
        }

        # 常见PID文件路径
        common_pid_paths = [
            '/var/run/nginx.pid',
            '/var/run/nginx/nginx.pid',
            '/usr/local/nginx/logs/nginx.pid',
            '/etc/nginx/nginx.pid'
        ]

        # 查找PID文件
        for pid_path in common_pid_paths:
            if os.path.exists(pid_path):
                runtime_info['pid_file'] = pid_path
                break

        # 常见锁文件路径
        common_lock_paths = [
            '/var/lock/nginx.lock',
            '/var/lock/subsys/nginx',
            '/run/lock/nginx.lock'  # NOSONAR
        ]

        # 查找锁文件
        for lock_path in common_lock_paths:
            if os.path.exists(lock_path):
                runtime_info['lock_file'] = lock_path
                break

        return runtime_info

    except Exception as e:
        logger.error(f'获取运行时路径信息失败: {e}')
        return {
            'pid_file': '获取失败',
            'lock_file': '获取失败'
        }