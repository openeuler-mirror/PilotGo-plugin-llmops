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

def save_config_file(cfg_filepath):
    """备份配置文件"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = '/tmp/nginx_config_backups'  # NOSONAR
        os.makedirs(backup_dir, exist_ok=True)

        backup_filename = f"nginx.conf.backup.{timestamp}"
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(cfg_filepath, backup_path)
        return backup_path
    except Exception as e:
        logger.warning(f'配置文件备份失败: {e}')
        return None

def recover_config_file(cfg_filepath, backup_path):
    """恢复配置文件"""
    try:
        shutil.copy2(backup_path, cfg_filepath)
        return True
    except Exception as e:
        logger.error(f'配置文件恢复失败: {e}')
        return False

def modify_timeout_config(cfg_filepath, params):
    """更新配置文件中的超时时间设置"""
    try:
        # 读取配置文件内容
        with open(cfg_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_path = temp_file.name

            # 处理每一行
            lines = body.split('\n')
            updated_lines = []
            params_updated = set()

            for line in lines:
                updated_line = line
                for param_name, param_value in params.items():
                    # 检查是否已经包含该配置
                    pattern = rf'^\s*{param_name}\s+[^;]+;'
                    if re.match(pattern, line.strip()):  # NOSONAR
                        # 替换现有配置
                        updated_line = f"{param_name} {param_value};"
                        params_updated.add(param_name)
                        break

                updated_lines.append(updated_line)

            # 添加未设置的配置到http块
            if params_updated:
                # 查找http块位置
                http_block_start = -1
                http_block_end = -1
                brace_count = 0
                in_http_block = False

                for i, line in enumerate(lines):
                    if 'http' in line and '{' in line:
                        in_http_block = True
                        http_block_start = i
                        brace_count = 1
                    elif in_http_block:
                        if '{' in line:
                            brace_count += 1
                        if '}' in line:
                            brace_count -= 1
                            if brace_count == 0:
                                http_block_end = i
                                break

                # 在http块内添加新配置
                if http_block_start != -1 and http_block_end != -1:
                    for param_name, param_value in params.items():
                        if param_name not in params_updated:
                            # 在http块内合适位置插入新配置
                            insert_pos = http_block_start + 1
                            # 查找已有超时配置的位置
                            for i in range(http_block_start + 1, http_block_end):
                                if any(timeout_param in lines[i] for timeout_param in [
                                    'client_body_timeout', 'client_header_timeout',
                                    'keepalive_timeout', 'send_timeout'
                                ]):
                                    insert_pos = i + 1
                                    break

                            # 插入新配置
                            updated_lines.insert(insert_pos, f"    {param_name} {param_value};")
                            params_updated.add(param_name)

            # 写入临时文件
            temp_file.write('\n'.join(updated_lines))

        # 替换原始文件
        shutil.move(temp_path, cfg_filepath)

        return {'success': True, 'updated_params': list(params_updated)}

    except Exception as e:
        logger.error(f'更新超时配置失败: {e}')
        return {'success': False, 'error': str(e)}

def certify_nginx_config():
    """验证Nginx配置文件语法"""
    try:
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        return {'valid': True} if output.returncode == 0 else {'valid': False, 'error': output.stderr}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def reload_nginx_config(method):
    """重新加载Nginx配置"""
    try:
        if method == 'graceful':
            # 平滑重载
            output = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)
        elif method == 'restart':
            # 重启服务
            output = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)
            if output.returncode != 0:
                # 尝试使用service命令
                output = subprocess.run(['service', 'nginx', 'restart'], capture_output=True, text=True)
        else:
            return {'success': False, 'error': f'不支持的重载方式: {method}'}

        return {'success': True} if output.returncode == 0 else {'success': False, 'error': output.stderr}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def fetch_timeout_config_recommendations():
    """获取超时时间配置推荐值"""
    recommendations = {
        'client_body_timeout': '60s',
        'client_header_timeout': '60s',
        'keepalive_timeout': '75s',
        'send_timeout': '60s',
        'proxy_connect_timeout': '60s',
        'proxy_send_timeout': '60s',
        'proxy_read_timeout': '60s',
        'fastcgi_connect_timeout': '60s',
        'fastcgi_send_timeout': '60s',
        'fastcgi_read_timeout': '60s',
        'client_max_body_size': '10m'
    }
    return recommendations

# 工具配置
TOOL_CONFIG = {
    "name": "set_nginx_runtime_timeout",
    "function": set_nginx_runtime_timeout,
    "description": "设置Nginx的各种超时时间配置，包括请求/连接/发送/接收超时时间、客户端保持连接超时时间",
    "parameters": {
        "type": "object",
        "properties": {
            "client_body_timeout": {
                "type": "string",
                "description": "客户端请求体超时时间（如：60s, 5m, 1h）"
            },
            "client_header_timeout": {
                "type": "string",
                "description": "客户端请求头超时时间（如：60s, 5m, 1h）"
            },
            "keepalive_timeout": {
                "type": "string",
                "description": "客户端保持连接超时时间（如：75s, 5m）"
            },
            "send_timeout": {
                "type": "string",
                "description": "发送超时时间（如：60s, 5m）"
            },
            "proxy_connect_timeout": {
                "type": "string",
                "description": "代理连接超时时间（如：60s, 5m）"
            },
            "proxy_send_timeout": {
                "type": "string",
                "description": "代理发送超时时间（如：60s, 5m）"
            },
            "proxy_read_timeout": {
                "type": "string",
                "description": "代理读取超时时间（如：60s, 5m）"
            },
            "fastcgi_connect_timeout": {
                "type": "string",
                "description": "FastCGI连接超时时间（如：60s, 5m）"
            },
            "fastcgi_send_timeout": {
                "type": "string",
                "description": "FastCGI发送超时时间（如：60s, 5m）"
            },
            "fastcgi_read_timeout": {
                "type": "string",
                "description": "FastCGI读取超时时间（如：60s, 5m）"
            },
            "uwsgi_connect_timeout": {
                "type": "string",
                "description": "uWSGI连接超时时间（如：60s, 5m）"
            },
            "uwsgi_send_timeout": {
                "type": "string",
                "description": "uWSGI发送超时时间（如：60s, 5m）"
            },
            "uwsgi_read_timeout": {
                "type": "string",
                "description": "uWSGI读取超时时间（如：60s, 5m）"
            },
            "scgi_connect_timeout": {
                "type": "string",
                "description": "SCGI连接超时时间（如：60s, 5m）"
            },
            "scgi_send_timeout": {
                "type": "string",
                "description": "SCGI发送超时时间（如：60s, 5m）"
            },
            "scgi_read_timeout": {
                "type": "string",
                "description": "SCGI读取超时时间（如：60s, 5m）"
            },
            "resolver_timeout": {
                "type": "string",
                "description": "DNS解析超时时间（如：30s, 5m）"
            },
            "client_max_body_size": {
                "type": "string",
                "description": "客户端最大请求体大小（如：10m, 100m, 1g）"
            },
            "reload_method": {
                "type": "string",
                "enum": ["graceful", "restart", "none"],
                "description": "重载方式：graceful(平滑重载)、restart(重启服务)、none(不重载)"
            }
        },
        "required": []
    }
}

# 工具配置
TOOL_CONFIG = {
    "name": "ngx_set_run_timeout",
    "function": set_nginx_runtime_timeout,
    "description": "设置Nginx的各种超时时间配置，包括请求/连接/发送/接收超时时间、客户端保持连接超时时间",
    "parameters": {
        "type": "object",
        "properties": {
            "client_body_timeout": {
                "type": "string",
                "description": "客户端请求体超时时间（如：60s, 5m, 1h）"
            },
            "client_header_timeout": {
                "type": "string",
                "description": "客户端请求头超时时间（如：60s, 5m, 1h）"
            },
            "keepalive_timeout": {
                "type": "string",
                "description": "客户端保持连接超时时间（如：75s, 5m）"
            },
            "send_timeout": {
                "type": "string",
                "description": "发送超时时间（如：60s, 5m）"
            },
        }
    }
}
