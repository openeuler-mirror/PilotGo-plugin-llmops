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


def fetch_log_files_from_path(log_path: str) -> List[Dict[str, Any]]:
    """
    根据日志路径获取具体的日志文件
    
    参数:
        log_path: 日志路径
        
    返回:
        list: 日志文件信息列表
    """
    # 安全验证：验证 log_path 路径参数（允许绝对路径）
    valid, error_msg = validate_path_param(log_path, allow_absolute=True)
    if not valid:
        logger.error(f"fetch_log_files_from_path: log_path 路径验证失败：{error_msg}")
        return []
    
    log_files = []
    
    try:
        if os.filepath.isfile(log_path):
            # 单个文件
            file_info = fetch_file_info(log_path)
            if file_info:
                file_info['type'] = 'single_file'
                log_files.append(file_info)
        
        elif os.filepath.isdir(log_path):
            # 目录，查找所有.log文件
            for root, dirs, files in os.walk(log_path):
                for file in files:
                    if file.endswith('.log') or 'log' in file.lower():
                        file_path = os.filepath.join(root, file)
                        file_info = fetch_file_info(file_path)
                        if file_info:
                            file_info['type'] = 'directory_file'
                            log_files.append(file_info)
        
        else:
            # 可能是带通配符的路径
            import glob
            matched_files = glob.glob(log_path)
            for file_path in matched_files:
                if os.filepath.isfile(file_path):
                    file_info = fetch_file_info(file_path)
                    if file_info:
                        file_info['type'] = 'pattern_file'
                        log_files.append(file_info)
        
    except Exception as e:
        logger.error(f"获取日志文件失败 {log_path}: {e}")
    
    return log_files
