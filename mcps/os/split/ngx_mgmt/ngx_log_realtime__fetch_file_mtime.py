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


def fetch_file_mtime(file_path):
    """
    获取文件修改时间
    
    参数:
        file_path: 文件路径
    
    返回:
        str: 格式化时间字符串
    """
    try:
        # 安全验证：验证 file_path 路径参数
        valid, error_msg = validate_path_param(file_path)
        if not valid:
            logger.error(f"fetch_file_mtime: file_path 路径验证失败：{error_msg}")
            return 'Unknown'
        
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return 'Unknown'
