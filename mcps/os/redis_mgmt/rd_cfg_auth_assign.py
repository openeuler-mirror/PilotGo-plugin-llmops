#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
import subprocess
import sys

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def set_redis_password(password: str) -> Dict[str, Any]:  # NOSONAR
    """
    设置Redis访问密码

    参数:
        password: 新密码  # NOSONAR

    返回:
        设置结果信息字典
    """
    output = {
        'success': False,
        'old_password': '',  # NOSONAR
        'new_password': '***',  # NOSONAR
        'message': ''
    }

    try:
        get_output = execute_redis_command('CONFIG GET requirepass')
        if get_output:
            lines = get_output.split('\n')
            if len(lines) >= 2:
                output['old_password'] = '***' if lines[1] else ''  # NOSONAR

        if not password:  # NOSONAR
            set_output = execute_redis_command('CONFIG SET requirepass ""')
        else:
            set_output = execute_redis_command(f'CONFIG SET requirepass {password}')  # NOSONAR

        if set_output and set_output == 'OK':
            output['success'] = True
            if password:  # NOSONAR
                output['message'] = 'Redis访问密码已设置'
            else:
                output['message'] = 'Redis访问密码已清除'
        else:
            output['message'] = '设置Redis访问密码失败'

    except Exception as e:
        output['message'] = f'设置Redis访问密码时发生异常: {e}'
        logger.error(output['message'])

    return output
def activate_password_auth(enable: bool = True) -> Dict[str, Any]:  # NOSONAR
    """
    开启/关闭密码认证

    参数:
        enable: 是否开启密码认证

    返回:
        设置结果信息字典
    """
    output = {
        'success': False,
        'auth_enabled': enable,
        'message': ''
    }

    try:
        if enable:
            get_output = execute_redis_command('CONFIG GET requirepass')
            if get_output:
                lines = get_output.split('\n')
                if len(lines) >= 2 and lines[1]:
                    output['message'] = '密码认证已开启'
                    output['success'] = True
                    return output

            output['message'] = '密码认证开启失败：未设置密码'
        else:
            set_output = execute_redis_command('CONFIG SET requirepass ""')
            if set_output and set_output == 'OK':
                output['success'] = True
                output['message'] = '密码认证已关闭'
            else:
                output['message'] = '密码认证关闭失败'

    except Exception as e:
        output['message'] = f'设置密码认证时发生异常: {e}'
        logger.error(output['message'])

    return output
def build_acl_user(username: str,
                    password: Optional[str] = None,  # NOSONAR
                    enabled: bool = True,
                    categories: Optional[List[str]] = None,
                    commands: Optional[List[str]] = None,
                    keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    创建ACL用户

    参数:
        username: 用户名
        password: 密码  # NOSONAR
        enabled: 是否启用
        categories: 权限类别列表
        commands: 命令权限列表
        keys: 键权限列表

    返回:
        创建结果信息字典
    """
    output = {
        'success': False,
        'username': username,
        'message': ''
    }

    try:
        acl_command = f'ACL SETUSER {username}'

        if enabled:
            acl_command += ' on'
        else:
            acl_command += ' off'

        if password:  # NOSONAR
            acl_command += f' >{password}'  # NOSONAR
        else:
            acl_command += ' nopass'

        if categories:
            for category in categories:
                acl_command += f' @{category}'

        if commands:
            for command in commands:
                acl_command += f' +{command}'

        if keys:
            for key in keys:
                acl_command += f' ~{key}'

        set_output = execute_redis_command(acl_command)

        if set_output and set_output == 'OK':
            output['success'] = True
            output['message'] = f'ACL用户 {username} 创建成功'
        else:
            output['message'] = f'创建ACL用户 {username} 失败'

    except Exception as e:
        output['message'] = f'创建ACL用户时发生异常: {e}'
        logger.error(output['message'])

    return output
def modify_acl_user(username: str,
                   password: Optional[str] = None,  # NOSONAR
                   enabled: Optional[bool] = None,
                   categories: Optional[List[str]] = None,
                   commands: Optional[List[str]] = None,
                   keys: Optional[List[str]] = None,
                   reset: bool = False) -> Dict[str, Any]:
    """
    修改ACL用户

    参数:
        username: 用户名
        password: 密码  # NOSONAR
        enabled: 是否启用
        categories: 权限类别列表
        commands: 命令权限列表
        keys: 键权限列表
        reset: 是否重置用户权限

    返回:
        修改结果信息字典
    """
    output = {
        'success': False,
        'username': username,
        'message': ''
    }

    try:
        if reset:
            acl_command = f'ACL SETUSER {username} reset'
        else:
            acl_command = f'ACL SETUSER {username}'

            if enabled is not None:
                acl_command += ' on' if enabled else ' off'

            if password:  # NOSONAR
                acl_command += f' >{password}'  # NOSONAR

            if categories:
                for category in categories:
                    acl_command += f' @{category}'

            if commands:
                for command in commands:
                    acl_command += f' +{command}'

            if keys:
                for key in keys:
                    acl_command += f' ~{key}'

        set_output = execute_redis_command(acl_command)

        if set_output and set_output == 'OK':
            output['success'] = True
            output['message'] = f'ACL用户 {username} 修改成功'
        else:
            output['message'] = f'修改ACL用户 {username} 失败'

    except Exception as e:
        output['message'] = f'修改ACL用户时发生异常: {e}'
        logger.error(output['message'])

    return output
def remove_acl_user(username: str) -> Dict[str, Any]:
    """
    删除ACL用户

    参数:
        username: 用户名

    返回:
        删除结果信息字典
    """
    output = {
        'success': False,
        'username': username,
        'message': ''
    }

    try:
        delete_output = execute_redis_command(f'ACL DELUSER {username}')

        if delete_output and delete_output == 'OK':
            output['success'] = True
            output['message'] = f'ACL用户 {username} 删除成功'
        else:
            output['message'] = f'删除ACL用户 {username} 失败'

    except Exception as e:
        output['message'] = f'删除ACL用户时发生异常: {e}'
        logger.error(output['message'])

    return output
def fetch_redis_version() -> str:
    """
    获取Redis版本

    返回:
        Redis版本字符串
    """
    try:
        info_out = execute_redis_command('INFO server')
        if info_out:
            info_map = parse_redis_info(info_out)
            if 'server.redis_version' in info_map:
                return info_map['server.redis_version']
    except Exception as e:
        logger.warning(f"获取Redis版本失败: {e}")

    return '0.0.0'
def redis_config_auth_set(action: str = 'set_password',  # NOSONAR
                         username: Optional[str] = None,
                         password: Optional[str] = None,  # NOSONAR
                         enabled: Optional[bool] = None,
                         categories: Optional[List[str]] = None,
                         commands: Optional[List[str]] = None,
                         keys: Optional[List[str]] = None,
                         reset: bool = False) -> Dict[str, Any]:
    """
    设置/修改Redis访问密码、开启/关闭密码认证、配置ACL权限规则

    参数:
        action: 操作类型，可选值：
               - "set_password": 设置Redis访问密码  # NOSONAR
               - "enable_auth": 开启/关闭密码认证
               - "create_user": 创建ACL用户
               - "modify_user": 修改ACL用户
               - "delete_user": 删除ACL用户
        username: 用户名（ACL操作）
        password: 密码  # NOSONAR
        enabled: 是否启用（ACL用户）
        categories: 权限类别列表（ACL用户）
        commands: 命令权限列表（ACL用户）
        keys: 键权限列表（ACL用户）
        reset: 是否重置用户权限（modify_user操作）

    返回:
        格式化的操作结果字典
    """
    output = {
        'success': False,
        'message': '',
        'data': {},
        'timestamp': datetime.now().isoformat()
    }

    try:
        rd_cli = get_redis_cli_command()
        if not rd_cli:
            output['message'] = '未找到redis-cli命令'
            return output

        test_output = execute_redis_command('PING')
        if not test_output or test_output.upper() != 'PONG':
            output['message'] = '无法连接到Redis服务器'
            return output

        redis_version = fetch_redis_version()
        version_parts = redis_version.split('.')
        major = int(version_parts[0]) if version_parts else 0

        if action == 'set_password':  # NOSONAR
            if password is None:  # NOSONAR
                output['message'] = '缺少参数: password'  # NOSONAR
                return output

            set_result = set_redis_password(password)  # NOSONAR
            output['data'] = set_result
            output['success'] = set_result['success']
            output['message'] = set_result['message']

        elif action == 'enable_auth':
            if enabled is None:
                output['message'] = '缺少参数: enabled'
                return output

            enable_result = activate_password_auth(enabled)  # NOSONAR
            output['data'] = enable_result
            output['success'] = enable_result['success']
            output['message'] = enable_result['message']

        elif action == 'create_user':
            if not username:
                output['message'] = '缺少参数: username'
                return output

            if major < 6:
                output['message'] = 'ACL功能需要Redis 6.0或更高版本'
                return output

            create_result = build_acl_user(username, password, enabled, categories, commands, keys)  # NOSONAR
            output['data'] = create_result
            output['success'] = create_result['success']
            output['message'] = create_result['message']

        elif action == 'modify_user':
            if not username:
                output['message'] = '缺少参数: username'
                return output

            if major < 6:
                output['message'] = 'ACL功能需要Redis 6.0或更高版本'
                return output

            modify_result = modify_acl_user(username, password, enabled, categories, commands, keys, reset)  # NOSONAR
            output['data'] = modify_result
            output['success'] = modify_result['success']
            output['message'] = modify_result['message']

        elif action == 'delete_user':
            if not username:
                output['message'] = '缺少参数: username'
                return output

            if major < 6:
                output['message'] = 'ACL功能需要Redis 6.0或更高版本'
                return output

            delete_result = remove_acl_user(username)
            output['data'] = delete_result
            output['success'] = delete_result['success']
            output['message'] = delete_result['message']

        else:
            output['message'] = f'不支持的操作类型: {action}'

    except Exception as e:
        output['message'] = f'配置认证时发生异常: {e}'
        logger.error(output['message'])

    return output

TOOL_CONFIG = {
    'name': 'rd_cfg_auth_assign',
    'function': redis_config_auth_set,
    'description': '设置/修改Redis访问密码、开启/关闭密码认证、配置ACL权限规则',
    'parameters': {
        'action': {
            'type': 'string',
            'description': '操作类型',
            'enum': ['set_password', 'enable_auth', 'create_user', 'modify_user', 'delete_user'],  # NOSONAR
            'default': 'set_password'  # NOSONAR
        },
        'username': {
            'type': 'string',
            'description': '用户名',
            'required': False
        },
        'password': {  # NOSONAR
            'type': 'string',
            'description': '密码',
            'required': False
        },
        'enabled': {
            'type': 'boolean',
            'description': '是否启用',
            'required': False
        },
        'categories': {
            'type': 'array',
            'description': '权限类别列表',
            'required': False
        },
        'commands': {
            'type': 'array',
            'description': '命令权限列表',
            'required': False
        },
        'keys': {
            'type': 'array',
            'description': '键权限列表',
            'required': False
        },
        'reset': {
            'type': 'boolean',
            'description': '是否重置用户权限',
            'default': False
        }
    },
    'returns': {
        'type': 'object',
        'description': '操作结果字典'
    }
}

if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'set_password'  # NOSONAR
    username = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None  # NOSONAR
    enabled = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else None
    reset = sys.argv[5].lower() == 'true' if len(sys.argv) > 5 else False

    output = redis_config_auth_set(action, username, password, enabled, None, None, None, reset)  # NOSONAR
    print(json.dumps(output, indent=2, ensure_ascii=False))
