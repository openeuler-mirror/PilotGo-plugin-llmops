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


def fetch_nginx_log_files(log_type):
    """
    获取 Nginx日志文件路径
    
    参数:
        log_type: 日志类型 ('access', 'error', 'both')
    
    返回:
        list: 日志文件信息列表
    """
    try:
        # 安全验证：验证 log_type 参数
        valid_log_types = ['access', 'error', 'both']
        if log_type not in valid_log_types:
            logger.error(f"fetch_nginx_log_files: log_type 参数不合法：{log_type}")
            return []
        
        log_files = []
        
        # 获取Nginx配置信息
        cfg_state = fetch_nginx_config_info()
        if cfg_state['config_file'] == 'Unknown':
            # 如果无法获取配置，使用默认路径
            return fetch_default_log_files(log_type)
        
        # 解析配置文件获取日志路径
        log_config = analyze_nginx_log_config(cfg_state['config_file'])
        
        # 根据日志类型选择文件
        if log_type in ['access', 'both']:
            for access_log in log_config['access_logs']:
                if access_log['path'] not in ['stderr', 'syslog'] and os.path.exists(access_log['path']):
                    log_files.append({
                        'path': access_log['path'],
                        'type': 'access',
                        'size': access_log.get('size', 'Unknown'),
                        'mtime': fetch_file_mtime(access_log['path'])
                    })
        
        if log_type in ['error', 'both']:
            for error_log in log_config['error_logs']:
                if error_log['path'] not in ['stderr', 'syslog'] and os.path.exists(error_log['path']):
                    log_files.append({
                        'path': error_log['path'],
                        'type': 'error',
                        'size': error_log.get('size', 'Unknown'),
                        'mtime': fetch_file_mtime(error_log['path'])
                    })
        
        # 如果没有找到日志文件，使用默认路径
        if not log_files:
            log_files = fetch_default_log_files(log_type)
        
        return log_files
        
    except Exception as e:
        logger.error(f'获取Nginx日志文件失败: {e}')
        return fetch_default_log_files(log_type)
