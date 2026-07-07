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


def analyze_nginx_log_config(config_file):
    """
    解析 Nginx 配置文件获取日志配置（从 nginx-log-path.py 复制）
    
    参数:
        config_file: 配置文件路径
    
    返回:
        dict: 日志配置信息
    """
    try:
        # 安全验证：验证 config_file 路径参数
        valid, error_msg = validate_path_param(config_file)
        if not valid:
            logger.error(f"analyze_nginx_log_config: config_file 路径验证失败：{error_msg}")
            return {
                'access_logs': [],
                'error_logs': []
            }
        
        log_info = {
            'access_logs': [],
            'error_logs': []
        }
        
        if not os.path.exists(config_file):
            return log_info
        
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 解析访问日志配置
        access_log_matches = re.findall(r'access_log\s+([^;]+);', body)  # NOSONAR
        for match in access_log_matches:
            access_log_info = analyze_access_log_directive(match.strip())
            if access_log_info:
                log_info['access_logs'].append(access_log_info)
        
        # 解析错误日志配置
        error_log_matches = re.findall(r'error_log\s+([^;]+);', body)  # NOSONAR
        for match in error_log_matches:
            error_log_info = analyze_error_log_directive(match.strip())
            if error_log_info:
                log_info['error_logs'].append(error_log_info)
        
        return log_info
        
    except Exception as e:
        logger.error(f'解析Nginx日志配置失败: {e}')
        return {
            'access_logs': [],
            'error_logs': []
        }
