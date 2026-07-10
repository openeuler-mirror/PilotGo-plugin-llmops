from datetime import datetime
import argparse
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_runtime_timeout')

def set_nginx_runtime_timeout(
    client_body_timeout=None,
    client_header_timeout=None,
    keepalive_timeout=None,
    send_timeout=None,
    proxy_connect_timeout=None,
    proxy_send_timeout=None,
    proxy_read_timeout=None,
    fastcgi_connect_timeout=None,
    fastcgi_send_timeout=None,
    fastcgi_read_timeout=None,
    uwsgi_connect_timeout=None,
    uwsgi_send_timeout=None,
    uwsgi_read_timeout=None,
    scgi_connect_timeout=None,
    scgi_send_timeout=None,
    scgi_read_timeout=None,
    resolver_timeout=None,
    client_max_body_size=None,
    reload_method='graceful'
):
    """
    设置Nginx的各种超时时间配置

    Args:
        client_body_timeout: 客户端请求体超时时间
        client_header_timeout: 客户端请求头超时时间
        keepalive_timeout: 客户端保持连接超时时间
        send_timeout: 发送超时时间
        proxy_connect_timeout: 代理连接超时时间
        proxy_send_timeout: 代理发送超时时间
        proxy_read_timeout: 代理读取超时时间
        fastcgi_connect_timeout: FastCGI连接超时时间
        fastcgi_send_timeout: FastCGI发送超时时间
        fastcgi_read_timeout: FastCGI读取超时时间
        uwsgi_connect_timeout: uWSGI连接超时时间
        uwsgi_send_timeout: uWSGI发送超时时间
        uwsgi_read_timeout: uWSGI读取超时时间
        scgi_connect_timeout: SCGI连接超时时间
        scgi_send_timeout: SCGI发送超时时间
        scgi_read_timeout: SCGI读取超时时间
        resolver_timeout: DNS解析超时时间
        client_max_body_size: 客户端最大请求体大小
        reload_method: 重载方式 ('graceful'|'restart'|'none')
    """
    try:
        output = []
        output.append('=== Nginx超时时间设置工具 ===')

        # 检查是否有设置参数
        timeout_params = {
            'client_body_timeout': client_body_timeout,
            'client_header_timeout': client_header_timeout,
            'keepalive_timeout': keepalive_timeout,
            'send_timeout': send_timeout,
            'proxy_connect_timeout': proxy_connect_timeout,
            'proxy_send_timeout': proxy_send_timeout,
            'proxy_read_timeout': proxy_read_timeout,
            'fastcgi_connect_timeout': fastcgi_connect_timeout,
            'fastcgi_send_timeout': fastcgi_send_timeout,
            'fastcgi_read_timeout': fastcgi_read_timeout,
            'uwsgi_connect_timeout': uwsgi_connect_timeout,
            'uwsgi_send_timeout': uwsgi_send_timeout,
            'uwsgi_read_timeout': uwsgi_read_timeout,
            'scgi_connect_timeout': scgi_connect_timeout,
            'scgi_send_timeout': scgi_send_timeout,
            'scgi_read_timeout': scgi_read_timeout,
            'resolver_timeout': resolver_timeout,
            'client_max_body_size': client_max_body_size
        }

        # 过滤掉None值
        active_params = {k: v for k, v in timeout_params.items() if v is not None}

        if not active_params:
            output.append('错误: 未提供任何超时时间参数')
            return '\n'.join(output)

        # 获取nginx进程信息
        proc_info = get_nginx_process_info()
        if proc_info['status'] == '已停止':
            output.append('错误: Nginx服务未运行')
            return '\n'.join(output)

        # 获取nginx配置文件路径
        cfg_filepath = get_nginx_config_path()
        if not cfg_filepath:
            output.append('错误: 无法获取Nginx配置文件路径')
            return '\n'.join(output)

        # 验证参数格式
        validation_result = certify_timeout_parameters(active_params)
        if not validation_result['valid']:
            output.append('参数验证失败:')
            for error in validation_result['errors']:
                output.append(f"  - {error}")
            return '\n'.join(output)

        # 备份原始配置文件
        backup_path = save_config_file(cfg_filepath)
        if backup_path:
            output.append(f'配置文件已备份到: {backup_path}')

        # 更新配置文件
        update_result = modify_timeout_config(cfg_filepath, active_params)

        if update_result['success']:
            output.append('配置文件更新成功')
            output.append('\n设置的超时时间:')
            for param_name, param_value in active_params.items():
                output.append(f"  {param_name}: {param_value}")

            # 验证配置文件语法
            syntax_result = certify_nginx_config()
            if syntax_result['valid']:
                output.append('配置文件语法验证: 通过')

                # 根据选择的重载方式重新加载配置
                if reload_method != 'none':
                    reload_result = reload_nginx_config(reload_method)
                    if reload_result['success']:
                        output.append(f'Nginx配置重载: {reload_method}方式成功')
                    else:
                        output.append(f'Nginx配置重载失败: {reload_result["error"]}')
                        # 恢复备份
                        if backup_path:
                            recover_config_file(cfg_filepath, backup_path)
                            output.append('已恢复原始配置文件')
                else:
                    output.append('未执行重载操作，请手动重载Nginx配置')
            else:
                output.append('配置文件语法验证失败:')
                output.append(f"  错误: {syntax_result['error']}")
                # 恢复备份
                if backup_path:
                    recover_config_file(cfg_filepath, backup_path)
                    output.append('已恢复原始配置文件')
        else:
            output.append('配置文件更新失败:')
            output.append(f"  错误: {update_result['error']}")
            # 恢复备份
            if backup_path:
                recover_config_file(cfg_filepath, backup_path)
                output.append('已恢复原始配置文件')

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'设置Nginx超时时间失败: {e}')
        return f'设置Nginx超时时间失败: {e}'

def certify_timeout_parameters(params):
    """验证超时时间参数格式"""
    errors = []

    # 时间参数验证规则
    time_pattern = r'^\d+[smhd]?$'  # NOSONAR
    size_pattern = r'^\d+[kKmMgG]?$'  # NOSONAR

    time_params = [
        'client_body_timeout', 'client_header_timeout', 'keepalive_timeout',
        'send_timeout', 'proxy_connect_timeout', 'proxy_send_timeout',
        'proxy_read_timeout', 'fastcgi_connect_timeout', 'fastcgi_send_timeout',
        'fastcgi_read_timeout', 'uwsgi_connect_timeout', 'uwsgi_send_timeout',
        'uwsgi_read_timeout', 'scgi_connect_timeout', 'scgi_send_timeout',
        'scgi_read_timeout', 'resolver_timeout'
    ]

    size_params = ['client_max_body_size']

    for param_name, param_value in params.items():
        if param_name in time_params:
            if not re.match(time_pattern, str(param_value)):  # NOSONAR
                errors.append(f'{param_name}: 格式错误，应为数字+单位(s/m/h/d)，如: 60s, 5m, 1h')

        elif param_name in size_params:
            if not re.match(size_pattern, str(param_value)):  # NOSONAR
                errors.append(f'{param_name}: 格式错误，应为数字+单位(k/m/g)，如: 10m, 1g, 512k')

    return {'valid': len(errors) == 0, 'errors': errors}