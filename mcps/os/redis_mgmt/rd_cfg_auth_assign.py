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
