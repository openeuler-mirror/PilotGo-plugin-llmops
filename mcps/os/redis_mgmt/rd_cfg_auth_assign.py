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
