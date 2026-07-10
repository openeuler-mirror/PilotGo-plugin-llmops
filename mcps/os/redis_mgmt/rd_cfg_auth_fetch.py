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
