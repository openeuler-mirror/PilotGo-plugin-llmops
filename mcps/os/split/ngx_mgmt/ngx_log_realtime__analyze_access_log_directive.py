#!/usr/bin/env python3

import subprocess
import platform
import os
import re
import logging
import time
import threading
import select
from datetime import datetime
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from .utils import (

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_real_time')


def analyze_access_log_directive(directive):
    """
    解析access_log指令（从nginx-log-path.py复制）
    """
    try:
        parts = directive.split()
        if not parts:
            return None
        
        log_info = {
            'path': 'Unknown',
            'size': 'Unknown'
        }
        
        log_info['path'] = parts[0]
        
        if os.path.exists(log_info['path']):
            try:
                size = os.path.getsize(log_info['path'])
                log_info['size'] = render_file_size(size)
            except Exception:
                log_info['size'] = '无法获取大小'
        
        return log_info
        
    except Exception as e:
        logger.error(f'解析access_log指令失败: {e}')
        return None
