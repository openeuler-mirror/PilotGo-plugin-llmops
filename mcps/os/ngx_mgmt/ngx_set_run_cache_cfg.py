from datetime import datetime
import logging
import os
import re
import shutil
import subprocess
import tempfile

import stat

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_runtime_cache_config')

def set_nginx_cache_config(
    cache_enabled=None,
    cache_path=None,
    cache_size=None,
    cache_inactive=None,
    cache_levels=None,
    cache_keys_zone=None,
    proxy_cache=None,
    fastcgi_cache=None,
    cache_method="proxy",
    reload_method='graceful'
):
    """
    设置Nginx缓存配置

    Args:
        cache_enabled: 是否启用缓存 (True/False)
        cache_path: 缓存路径
        cache_size: 缓存大小 (如: 100m, 1g)
        cache_inactive: 缓存过期时间 (如: 60m, 24h)
        cache_levels: 缓存目录层级 (如: 1:2)
        cache_keys_zone: 缓存键区大小 (如: cache_zone:10m)
        proxy_cache: proxy缓存区名称
        fastcgi_cache: fastcgi缓存区名称
        cache_method: 缓存类型 ("proxy"|"fastcgi")
        reload_method: 重载方式 ('graceful'|'restart'|'none')
    """
    try:
        output = []
        output.append('=== Nginx缓存配置设置工具 ===')

        # 检查是否有设置参数
        cache_params = {
            'cache_enabled': cache_enabled,
            'cache_path': cache_path,
            'cache_size': cache_size,
            'cache_inactive': cache_inactive,
            'cache_levels': cache_levels,
            'cache_keys_zone': cache_keys_zone,
            'proxy_cache': proxy_cache,
            'fastcgi_cache': fastcgi_cache
        }

        # 过滤掉None值
        active_params = {k: v for k, v in cache_params.items() if v is not None}

        if not active_params:
            output.append('错误: 未提供任何缓存配置参数')
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
        validation_result = certify_cache_parameters(active_params, cache_method)
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
        update_result = modify_cache_config(cfg_filepath, active_params, cache_method)

        if update_result['success']:
            output.append('配置文件更新成功')
            output.append('\n设置的缓存配置:')
            for param_name, param_value in active_params.items():
                output.append(f"  {param_name}: {param_value}")

            # 验证配置文件语法
            syntax_result = certify_nginx_config()
            if syntax_result['valid']:
                output.append('配置文件语法验证: 通过')

                # 处理缓存路径创建
                if cache_path and cache_enabled is not False:
                    path_result = build_cache_directory(cache_path)
                    if path_result['success']:
                        output.append(f'缓存目录创建: {cache_path} 成功')
                    else:
                        output.append(f'缓存目录创建失败: {path_result["error"]}')

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
        logger.error(f'设置Nginx缓存配置失败: {e}')
        return f'设置Nginx缓存配置失败: {e}'

def certify_cache_parameters(params, cache_method):
    """验证缓存配置参数格式"""
    errors = []

    # 大小参数验证规则
    size_pattern = r'^\d+[kKmMgG]?$'  # NOSONAR
    time_pattern = r'^\d+[smhd]?$'  # NOSONAR
    levels_pattern = r'^\d+:\d+$'  # NOSONAR
    keys_zone_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*:\d+[mM]$'  # NOSONAR

    if 'cache_enabled' in params:
        if params['cache_enabled'] not in [True, False, 'true', 'false', '1', '0']:
            errors.append('cache_enabled: 必须为 true/false 或 1/0')

    if 'cache_path' in params:
        if not isinstance(params['cache_path'], str) or not params['cache_path'].strip():
            errors.append('cache_path: 必须为非空字符串')
        elif not params['cache_path'].startswith('/'):
            errors.append('cache_path: 必须为绝对路径')
        else:
            # 使用通用验证函数进行路径验证
            is_valid, error_msg = validate_identifier_param(params['cache_path'], allow_slash=True)
            if not is_valid:
                errors.append(f'cache_path: 格式不合法 - {error_msg}')

    if 'cache_size' in params:
        if not re.match(size_pattern, str(params['cache_size'])):  # NOSONAR
            errors.append('cache_size: 格式错误，应为数字+单位(k/m/g)，如: 100m, 1g')

    if 'cache_inactive' in params:
        if not re.match(time_pattern, str(params['cache_inactive'])):  # NOSONAR
            errors.append('cache_inactive: 格式错误，应为数字+单位(s/m/h/d)，如: 60m, 24h')

    if 'cache_levels' in params:
        if not re.match(levels_pattern, str(params['cache_levels'])):  # NOSONAR
            errors.append('cache_levels: 格式错误，应为 数字:数字，如: 1:2')

    if 'cache_keys_zone' in params:
        if not re.match(keys_zone_pattern, str(params['cache_keys_zone'])):  # NOSONAR
            errors.append('cache_keys_zone: 格式错误，应为 名称:大小，如: cache_zone:10m')

    if 'proxy_cache' in params and cache_method == "proxy":
        if not isinstance(params['proxy_cache'], str) or not params['proxy_cache'].strip():
            errors.append('proxy_cache: 必须为非空字符串')

    if 'fastcgi_cache' in params and cache_method == "fastcgi":
        if not isinstance(params['fastcgi_cache'], str) or not params['fastcgi_cache'].strip():
            errors.append('fastcgi_cache: 必须为非空字符串')

    return {'valid': len(errors) == 0, 'errors': errors}

def build_cache_directory(cache_path):
    """创建缓存目录并设置权限"""
    try:
        # 安全验证：验证 cache_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cache_path, allow_absolute=True)
        if not valid:
            logger.error(f"build_cache_directory: cache_path 路径验证失败：{error_msg}")
            return {'success': False, 'error': f'缓存路径不安全：{error_msg}'}

        # 创建目录
        os.makedirs(cache_path, exist_ok=True)

        # 设置目录权限 (nginx用户需要读写权限)
        os.chmod(cache_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)  # NOSONAR

        # 设置目录所有者为nginx用户（如果存在）
        try:
            # 尝试设置nginx用户为所有者
            subprocess.run(['chown', 'nginx:nginx', cache_path], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 如果nginx用户不存在或命令失败，继续
            pass

        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def save_config_file(cfg_filepath):
    """备份配置文件"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"save_config_file: cfg_filepath 路径验证失败：{error_msg}")
            return None

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
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"recover_config_file: cfg_filepath 路径验证失败：{error_msg}")
            return False

        # 安全验证：验证 backup_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(backup_path, allow_absolute=True)
        if not valid:
            logger.error(f"recover_config_file: backup_path 路径验证失败：{error_msg}")
            return False

        shutil.copy2(backup_path, cfg_filepath)
        return True
    except Exception as e:
        logger.error(f'配置文件恢复失败: {e}')
        return False

def modify_cache_config(cfg_filepath, params, cache_method):
    """更新配置文件中的缓存配置"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"modify_cache_config: cfg_filepath 路径验证失败：{error_msg}")
            return {'success': False, 'error': f'配置文件路径不安全：{error_msg}'}

        # 读取配置文件内容
        with open(cfg_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_path = temp_file.name

            # 处理缓存启用/禁用
            if 'cache_enabled' in params:
                if params['cache_enabled'] in [True, 'true', '1']:
                    # 启用缓存 - 添加或更新缓存配置
                    body = activate_cache_config(body, params, cache_method)
                else:
                    # 禁用缓存 - 注释掉缓存相关配置
                    body = deactivate_cache_config(body, cache_method)
            else:
                # 只更新特定配置
                body = modify_specific_cache_config(body, params, cache_method)

            # 写入临时文件
            temp_file.write(body)

        # 替换原始文件
        shutil.move(temp_path, cfg_filepath)

        return {'success': True, 'updated_params': list(params.keys())}

    except Exception as e:
        logger.error(f'更新缓存配置失败: {e}')
        return {'success': False, 'error': str(e)}