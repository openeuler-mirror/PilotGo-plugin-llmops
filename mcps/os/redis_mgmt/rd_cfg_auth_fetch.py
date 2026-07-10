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

def fetch_auth_config() -> Dict[str, Any]:
    """
    获取认证配置

    返回:
        认证配置信息字典
    """
    output = {
        'requirepass': '',
        'auth_enabled': False,
        'auth_type': 'password',  # NOSONAR
        'message': '获取认证配置'
    }

    try:
        cfg_out = execute_redis_command('CONFIG GET requirepass')
        if cfg_out:
            lines = cfg_out.split('\n')
            if len(lines) >= 2 and lines[1]:
                output['requirepass'] = '***' if lines[1] else ''
                output['auth_enabled'] = bool(lines[1])

        info_out = execute_redis_command('INFO server')
        if info_out:
            info_map = parse_redis_info(info_out)

            if 'server.redis_version' in info_map:
                ver = info_map['server.redis_version']
                version_parts = ver.split('.')
                major = int(version_parts[0]) if version_parts else 0

                if major >= 6:
                    output['auth_type'] = 'acl'

        output['message'] = f'认证配置获取成功，认证类型: {output["auth_type"]}'

    except Exception as e:
        output['message'] = f'获取认证配置时发生异常: {e}'
        logger.error(output['message'])

    return output
def fetch_acl_users() -> Dict[str, Any]:
    """
    获取ACL用户列表

    返回:
        ACL用户列表信息字典
    """
    output = {
        'users': [],
        'total_users': 0,
        'default_user': 'default',
        'message': '获取ACL用户列表'
    }

    try:
        acl_output = execute_redis_command('ACL LIST')
        if acl_output:
            users = acl_output.split('\n')

            for user_line in users:
                if not user_line.strip():
                    continue

                user_info = analyze_acl_user(user_line)
                if user_info:
                    output['users'].append(user_info)

            output['total_users'] = len(output['users'])
            output['message'] = f'获取到 {output["total_users"]} 个ACL用户'

    except Exception as e:
        output['message'] = f'获取ACL用户列表时发生异常: {e}'
        logger.error(output['message'])

    return output
def analyze_acl_user(user_line: str) -> Optional[Dict[str, Any]]:
    """
    解析ACL用户信息

    参数:
        user_line: ACL用户信息行

    返回:
        ACL用户信息字典
    """
    try:
        parts = user_line.split()

        if not parts or not parts[0].startswith('user '):
            return None

        user_info = {
            'username': parts[0][5:],
            'flags': [],
            'passwords': [],  # NOSONAR
            'categories': [],
            'commands': [],
            'keys': []
        }

        for part in parts[1:]:
            if part.startswith('on'):
                user_info['flags'].append('on')
            elif part.startswith('off'):
                user_info['flags'].append('off')
            elif part.startswith('nopass'):
                user_info['flags'].append('nopass')
            elif part.startswith('#') and len(part) > 1:
                user_info['passwords'].append(part)  # NOSONAR
            elif part.startswith('>'):
                user_info['passwords'].append(part)  # NOSONAR
            elif part.startswith('~'):
                user_info['keys'].append(part[1:])
            elif part.startswith('@'):
                user_info['categories'].append(part[1:])
            elif part.startswith('+'):
                user_info['commands'].append(part[1:])
            elif part.startswith('-'):
                user_info['commands'].append(part)
            elif part.startswith('allkeys'):
                user_info['keys'].append('*')
            elif part.startswith('allchannels'):
                user_info['channels'].append('*')
            elif part.startswith('&'):
                user_info['channels'].append(part[1:])

        return user_info

    except Exception as e:
        logger.warning(f"解析ACL用户信息失败: {e}")
        return None
def fetch_acl_rules() -> Dict[str, Any]:
    """
    获取ACL规则列表

    返回:
        ACL规则列表信息字典
    """
    output = {
        'rules': [],
        'total_rules': 0,
        'message': '获取ACL规则列表'
    }

    try:
        users_result = fetch_acl_users()

        for user in users_result['users']:
            user_rules = {
                'username': user['username'],
                'flags': user['flags'],
                'passwords': user['passwords'],  # NOSONAR
                'categories': user['categories'],
                'commands': user['commands'],
                'keys': user['keys'],
                'total_permissions': len(user['categories']) + len(user['commands']) + len(user['keys'])
            }

            output['rules'].append(user_rules)

        output['total_rules'] = len(output['rules'])
        output['message'] = f'获取到 {output["total_rules"]} 个用户的ACL规则'

    except Exception as e:
        output['message'] = f'获取ACL规则列表时发生异常: {e}'
        logger.error(output['message'])

    return output
def fetch_password_encryption() -> Dict[str, Any]:  # NOSONAR
    """
    获取密码加密方式

    返回:
        密码加密方式信息字典
    """
    output = {
        'encryption_method': 'unknown',
        'hash_algorithm': 'unknown',
        'message': '获取密码加密方式'
    }

    try:
        info_out = execute_redis_command('INFO server')
        if info_out:
            info_map = parse_redis_info(info_out)

            if 'server.redis_version' in info_map:
                ver = info_map['server.redis_version']
                version_parts = ver.split('.')
                major = int(version_parts[0]) if version_parts else 0
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0

                if major >= 6:
                    output['encryption_method'] = 'ACL'
                    output['hash_algorithm'] = 'SHA256'
                elif major >= 4:
                    output['encryption_method'] = 'requirepass'
                    output['hash_algorithm'] = 'SHA256'
                else:
                    output['encryption_method'] = 'requirepass'
                    output['hash_algorithm'] = 'SHA1'

        output['message'] = f'密码加密方式: {output["encryption_method"]}, 算法: {output["hash_algorithm"]}'

    except Exception as e:
        output['message'] = f'获取密码加密方式时发生异常: {e}'
        logger.error(output['message'])

    return output
