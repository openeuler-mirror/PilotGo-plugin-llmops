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


def fetch_default_log_files(log_type):
    """
    获取默认的 Nginx日志文件路径
    
    参数:
        log_type: 日志类型
    
    返回:
        list: 默认日志文件列表
    """
    try:
        # 安全验证：验证 log_type 参数
        valid_log_types = ['access', 'error', 'both']
        if log_type not in valid_log_types:
            logger.error(f"fetch_default_log_files: log_type 参数不合法：{log_type}")
            return []
        
        log_files = []
        common_log_dirs = ['/var/log/nginx', '/usr/local/nginx/logs', '/var/log']
        
        for log_dir in common_log_dirs:
            if os.path.exists(log_dir):
                # 访问日志文件
                if log_type in ['access', 'both']:
                    access_logs = [
                        os.path.join(log_dir, 'access.log'),
                        os.path.join(log_dir, 'access_log'),
                        os.path.join(log_dir, 'nginx-access.log')
                    ]
                    for log_path in access_logs:
                        if os.path.exists(log_path):
                            log_files.append({
                                'path': log_path,
                                'type': 'access',
                                'size': render_file_size(os.path.getsize(log_path)),
                                'mtime': fetch_file_mtime(log_path)
                            })
                            break
                
                # 错误日志文件
                if log_type in ['error', 'both']:
                    error_logs = [
                        os.path.join(log_dir, 'error.log'),
                        os.path.join(log_dir, 'error_log'),
                        os.path.join(log_dir, 'nginx-error.log')
                    ]
                    for log_path in error_logs:
                        if os.path.exists(log_path):
                            log_files.append({
                                'path': log_path,
                                'type': 'error',
                                'size': render_file_size(os.path.getsize(log_path)),
                                'mtime': fetch_file_mtime(log_path)
                            })
                            break
                
                # 如果找到了文件，不再检查其他目录
                if log_files:
                    break
        
        return log_files
        
    except Exception as e:
        logger.error(f'获取默认日志文件失败: {e}')
        return []
