#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_size')


def fetch_disk_usage(file_path: str) -> Dict[str, Any]:
    """
    获取文件磁盘使用情况
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 磁盘使用信息
    """
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_disk_usage: file_path 路径验证失败：{error_msg}")
            return {
                'filesystem': 'error',
                'total_size': 'error',
                'used': 'error',
                'available': 'error',
                'use_percent': 'error',
                'mount_point': 'error'
            }
        
        # 获取文件所在磁盘信息
        output = subprocess.run(['df', '-h', file_path], capture_output=True, text=True)
        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    return {
                        'filesystem': parts[0],
                        'total_size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mount_point': parts[5] if len(parts) > 5 else ''
                    }
        
        return {
            'filesystem': 'unknown',
            'total_size': 'unknown',
            'used': 'unknown',
            'available': 'unknown',
            'use_percent': 'unknown',
            'mount_point': 'unknown'
        }
        
    except Exception as e:
        logger.error(f"获取磁盘使用情况失败 {file_path}: {e}")
        return {
            'filesystem': 'error',
            'total_size': 'error',
            'used': 'error',
            'available': 'error',
            'use_percent': 'error',
            'mount_point': 'error'
        }
