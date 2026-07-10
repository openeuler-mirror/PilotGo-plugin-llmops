import glob
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
logger = logging.getLogger('nginx_log_path')

def fetch_nginx_log_path():
    """
    获取Nginx访问日志和错误日志的存储路径、文件名称、日志格式的MCP工具

    返回:
        格式化的Nginx日志路径信息字符串，包含：
        - 访问日志路径和格式
        - 错误日志路径和格式
        - 日志轮转配置
        - 日志文件状态
        - 自定义日志格式定义
    """
    try:
        output = []
        output.append('=== Nginx日志路径和格式信息 ===')

        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('=============================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")

        # 获取主配置文件路径
        cfg_state = fetch_nginx_config_info()
        if cfg_state['config_file'] == 'Unknown':
            output.append(f"错误: 无法找到Nginx配置文件")
            output.append('=============================')
            return '\n'.join(output)

        output.append(f"主配置文件: {cfg_state['config_file']}")

        # 解析配置文件获取日志信息
        log_info = analyze_nginx_log_config(cfg_state['config_file'])

        # 显示访问日志信息
        output.append(f"\n=== 访问日志信息 ===")
        if log_info['access_logs']:
            for i, access_log in enumerate(log_info['access_logs'], 1):
                output.append(f"访问日志 {i}:")
                output.append(f"  路径: {access_log['path']}")
                output.append(f"  格式: {access_log['format']}")
                output.append(f"  缓冲区: {access_log['buffer']}")
                output.append(f"  刷新: {access_log['flush']}")
                output.append(f"  压缩: {access_log['gzip']}")
                output.append(f"  文件状态: {access_log['state']}")
                if access_log['size'] != 'Unknown':
                    output.append(f"  文件大小: {access_log['size']}")
        else:
            output.append("未找到访问日志配置")

        # 显示错误日志信息
        output.append(f"\n=== 错误日志信息 ===")
        if log_info['error_logs']:
            for i, error_log in enumerate(log_info['error_logs'], 1):
                output.append(f"错误日志 {i}:")
                output.append(f"  路径: {error_log['path']}")
                output.append(f"  级别: {error_log['level']}")
                output.append(f"  文件状态: {error_log['state']}")
                if error_log['size'] != 'Unknown':
                    output.append(f"  文件大小: {error_log['size']}")
        else:
            output.append("未找到错误日志配置")

        # 显示日志格式定义
        output.append(f"\n=== 日志格式定义 ===")
        if log_info['log_formats']:
            for format_name, format_string in log_info['log_formats'].items():
                output.append(f"格式 '{format_name}': {format_string}")
        else:
            output.append("未找到自定义日志格式定义")

        # 显示日志轮转配置
        output.append(f"\n=== 日志轮转配置 ===")
        if log_info['logrotate_config']:
            for config_item in log_info['logrotate_config']:
                output.append(config_item)
        else:
            output.append("未找到日志轮转配置")

        # 显示日志目录权限
        output.append(f"\n=== 日志目录权限 ===")
        for perm_info in log_info['directory_permissions']:
            output.append(perm_info)

        output.append('\n=============================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx日志路径信息失败: {e}')
        return f'获取Nginx日志路径信息失败: {e}'

def analyze_nginx_log_config(config_file):
    """
    解析Nginx配置文件获取日志相关信息

    参数:
        config_file: Nginx主配置文件路径

    返回:
        dict: 包含日志路径、格式、轮转配置等信息的字典
    """
    try:
        log_info = {
            'access_logs': [],
            'error_logs': [],
            'log_formats': {},
            'logrotate_config': [],
            'directory_permissions': []
        }

        if not os.path.exists(config_file):
            return log_info

        # 读取配置文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()

        # 解析访问日志配置
        access_log_matches = re.findall(r'access_log\s+([^;]+);', body)  # NOSONAR
        for match in access_log_matches:
            access_log_info = analyze_access_log_directive(match.strip())
            if access_log_info:
                log_info['access_logs'].append(access_log_info)

        # 解析错误日志配置
        error_log_matches = re.findall(r'error_log\s+([^;]+);', body)  # NOSONAR
        for match in error_log_matches:
            error_log_info = analyze_error_log_directive(match.strip())
            if error_log_info:
                log_info['error_logs'].append(error_log_info)

        # 解析日志格式定义
        log_format_matches = re.findall(r'log_format\s+([^}]+)}', body)  # NOSONAR
        for match in log_format_matches:
            format_info = analyze_log_format_directive(match.strip())
            if format_info:
                log_info['log_formats'].update(format_info)

        # 检查包含的配置文件
        include_matches = re.findall(r'include\s+([^;]+);', body)  # NOSONAR
        for match in include_matches:
            include_pattern = match.strip()
            # 处理通配符包含
            if '*' in include_pattern:
                included_files = glob.glob(include_pattern)
                for included_file in included_files:
                    if os.path.exists(included_file):
                        included_info = analyze_included_log_config(included_file)
                        log_info['access_logs'].extend(included_info['access_logs'])
                        log_info['error_logs'].extend(included_info['error_logs'])
                        log_info['log_formats'].update(included_info['log_formats'])
            else:
                if os.path.exists(include_pattern):
                    included_info = analyze_included_log_config(include_pattern)
                    log_info['access_logs'].extend(included_info['access_logs'])
                    log_info['error_logs'].extend(included_info['error_logs'])
                    log_info['log_formats'].update(included_info['log_formats'])

        # 获取日志轮转配置
        log_info['logrotate_config'] = fetch_logrotate_config()

        # 检查日志目录权限
        log_info['directory_permissions'] = verify_log_directory_permissions(log_info)

        return log_info

    except Exception as e:
        logger.error(f'解析Nginx日志配置失败: {e}')
        return {
            'access_logs': [],
            'error_logs': [],
            'log_formats': {},
            'logrotate_config': [],
            'directory_permissions': [f'解析配置失败: {e}']
        }

def analyze_access_log_directive(directive):
    """
    解析access_log指令

    参数:
        directive: access_log指令内容

    返回:
        dict: 访问日志信息字典
    """
    try:
        # 解析路径和格式
        parts = directive.split()
        if not parts:
            return None

        log_info = {
            'path': 'Unknown',
            'format': 'combined',  # 默认格式
            'buffer': '未设置',
            'flush': '未设置',
            'gzip': '未设置',
            'state': 'Unknown',
            'size': 'Unknown'
        }

        # 第一个参数是路径
        log_info['path'] = parts[0]

        # 检查路径状态
        if os.path.exists(log_info['path']):
            log_info['state'] = '存在'
            try:
                size = os.path.getsize(log_info['path'])
                log_info['size'] = render_file_size(size)
            except Exception:
                log_info['size'] = '无法获取大小'
        else:
            log_info['state'] = '不存在'

        # 检查其他参数
        for i, part in enumerate(parts[1:], 1):
            if part in ['buffer', 'gzip', 'flush']:
                log_info[part] = '已设置'
            elif part not in ['off']:  # 忽略off参数
                # 可能是日志格式名称
                log_info['format'] = part

        return log_info

    except Exception as e:
        logger.error(f'解析access_log指令失败: {e}')
        return None

def analyze_error_log_directive(directive):
    """
    解析error_log指令

    参数:
        directive: error_log指令内容

    返回:
        dict: 错误日志信息字典
    """
    try:
        parts = directive.split()
        if not parts:
            return None

        log_info = {
            'path': 'Unknown',
            'level': 'error',  # 默认级别
            'state': 'Unknown',
            'size': 'Unknown'
        }

        # 第一个参数是路径或stderr/syslog
        if parts[0] in ['stderr', 'syslog']:
            log_info['path'] = parts[0]
            log_info['state'] = '系统输出'
        else:
            log_info['path'] = parts[0]
            if os.path.exists(log_info['path']):
                log_info['state'] = '存在'
                try:
                    size = os.path.getsize(log_info['path'])
                    log_info['size'] = render_file_size(size)
                except Exception:
                    log_info['size'] = '无法获取大小'
            else:
                log_info['state'] = '不存在'

        # 检查日志级别
        log_levels = ['debug', 'info', 'notice', 'warn', 'error', 'crit', 'alert', 'emerg']
        for part in parts[1:]:
            if part in log_levels:
                log_info['level'] = part
                break

        return log_info

    except Exception as e:
        logger.error(f'解析error_log指令失败: {e}')
        return None

def analyze_log_format_directive(directive):
    """
    解析log_format指令

    参数:
        directive: log_format指令内容

    返回:
        dict: 日志格式信息字典
    """
    try:
        # 提取格式名称和定义
        match = re.match(r'(\w+)\s+(.+)', directive)  # NOSONAR
        if not match:
            return {}

        format_name = match.group(1)
        format_definition = match.group(2).strip()

        return {format_name: format_definition}

    except Exception as e:
        logger.error(f'解析log_format指令失败: {e}')
        return {}

def analyze_included_log_config(config_file):
    """
    解析被包含的配置文件

    参数:
        config_file: 被包含的配置文件路径

    返回:
        dict: 包含的日志配置信息
    """
    try:
        included_info = {
            'access_logs': [],
            'error_logs': [],
            'log_formats': {}
        }

        if not os.path.exists(config_file):
            return included_info

        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()

        # 解析访问日志
        access_log_matches = re.findall(r'access_log\s+([^;]+);', body)  # NOSONAR
        for match in access_log_matches:
            access_log_info = analyze_access_log_directive(match.strip())
            if access_log_info:
                included_info['access_logs'].append(access_log_info)

        # 解析错误日志
        error_log_matches = re.findall(r'error_log\s+([^;]+);', body)  # NOSONAR
        for match in error_log_matches:
            error_log_info = analyze_error_log_directive(match.strip())
            if error_log_info:
                included_info['error_logs'].append(error_log_info)

        # 解析日志格式
        log_format_matches = re.findall(r'log_format\s+([^}]+)}', body)  # NOSONAR
        for match in log_format_matches:
            format_info = analyze_log_format_directive(match.strip())
            if format_info:
                included_info['log_formats'].update(format_info)

        return included_info

    except Exception as e:
        logger.error(f'解析包含的配置文件失败: {e}')
        return {
            'access_logs': [],
            'error_logs': [],
            'log_formats': {}
        }