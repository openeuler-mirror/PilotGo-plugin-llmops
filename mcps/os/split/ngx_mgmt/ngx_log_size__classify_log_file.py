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


def classify_log_file(file_path: str) -> Dict[str, Any]:
    """
    分类日志文件类型
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 分类信息
    """
    classification = {
        'log_type': 'unknown',
        'is_rotated': False,
        'rotation_number': 0,
        'is_compressed': False
    }
    
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"classify_log_file: file_path 路径验证失败：{error_msg}")
            return classification
        
        file_name = os.filepath.basename(file_path)
        
        # 检查是否是轮转文件
        rotation_patterns = [
            r'\.log\.(\d+)$',  # access.log.1
            r'\.log-(\d{8})$',  # access.log-20231201
            r'\.log\.(\d+)\.gz$',  # access.log.1.gz
        ]
        
        for pattern in rotation_patterns:
            match = re.search(pattern, file_name)  # NOSONAR
            if match:
                classification['is_rotated'] = True
                classification['rotation_number'] = int(match.group(1)) if match.group(1).isdigit() else 0
                break
        
        # 检查是否是压缩文件
        if file_name.endswith('.gz') or file_name.endswith('.bz2') or file_name.endswith('.xz'):
            classification['is_compressed'] = True
        
        # 判断日志类型
        if 'access' in file_name.lower():
            classification['log_type'] = 'access'
        elif 'error' in file_name.lower():
            classification['log_type'] = 'error'
        elif 'debug' in file_name.lower():
            classification['log_type'] = 'debug'
        elif 'slow' in file_name.lower():
            classification['log_type'] = 'slow'
        
    except Exception as e:
        logger.error(f"分类日志文件失败 {file_path}: {e}")
    
    return classification
