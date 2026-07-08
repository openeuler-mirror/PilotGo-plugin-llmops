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


def locate_possible_log_files(log_path: str) -> List[Dict[str, Any]]:
    """
    查找可能的日志文件
    
    参数:
        log_path: 日志路径
        
    返回:
        list: 可能的日志文件列表
    """
    # 安全验证：验证 log_path 路径参数（允许绝对路径）
    valid, error_msg = validate_path_param(log_path, allow_absolute=True)
    if not valid:
        logger.error(f"locate_possible_log_files: log_path 路径验证失败：{error_msg}")
        return []
    
    possible_files = []
    
    try:
        # 如果路径是相对路径，尝试在常见位置查找
        if not os.filepath.isabs(log_path):
            common_dirs = [
                '/var/log/nginx',
                '/usr/local/nginx/logs',
                '/opt/nginx/logs',
                '/var/log'
            ]
            
            for base_dir in common_dirs:
                full_path = os.filepath.join(base_dir, log_path)
                if os.filepath.exists(full_path):
                    file_info = fetch_file_info(full_path)
                    if file_info:
                        file_info['type'] = 'resolved_file'
                        possible_files.append(file_info)
        
        # 尝试查找轮转的日志文件
        base_name = os.filepath.basename(log_path)
        dir_name = os.filepath.dirname(log_path) if os.filepath.isabs(log_path) else '/var/log/nginx'
        
        if os.filepath.isdir(dir_name):
            for file in os.listdir(dir_name):
                if file.startswith(base_name) and (file.endswith('.log') or '.log.' in file):
                    file_path = os.filepath.join(dir_name, file)
                    file_info = fetch_file_info(file_path)
                    if file_info:
                        file_info['type'] = 'rotated_file'
                        possible_files.append(file_info)
        
    except Exception as e:
        logger.error(f"查找可能日志文件失败 {log_path}: {e}")
    
    return possible_files
