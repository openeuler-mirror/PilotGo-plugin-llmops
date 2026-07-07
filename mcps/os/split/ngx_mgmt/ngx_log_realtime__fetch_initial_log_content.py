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


def fetch_initial_log_content(log_files, lines, filter_keyword):
    """
    获取初始日志内容
    
    参数:
        log_files: 日志文件列表
        lines: 显示行数
        filter_keyword: 关键词过滤
    
    返回:
        list: 日志内容列表
    """
    try:
        # 安全验证：验证 lines 参数
        if not isinstance(lines, int) or lines <= 0 or lines > 10000:
            logger.error(f"fetch_initial_log_content: lines 参数不合法：{lines}")
            lines = 50  # 使用默认值
        
        # 安全验证：验证 filter_keyword 参数（如果提供）
        if filter_keyword is not None:
            valid, error_msg = validate_identifier_param(filter_keyword)
            if not valid:
                logger.error(f"fetch_initial_log_content: filter_keyword 验证失败：{error_msg}")
                return [f"关键词过滤参数不安全：{error_msg}"]
        
        body = []
        
        for log_file in log_files:
            # 使用tail命令获取最后几行
            cmd = ['tail', f'-n{lines}', log_file['path']]
            
            if filter_keyword:
                # 使用grep过滤
                output = subprocess.run(['grep', filter_keyword, log_file['path']], capture_output=True, text=True)
                if output.returncode == 0:
                    lines_content = output.stdout.strip().split('\n')[-lines:]
                    for line in lines_content:
                        if line.strip():
                            body.append(f"[{log_file['type']}] {line.strip()}")
            else:
                # 直接获取最后几行
                output = subprocess.run(cmd, capture_output=True, text=True)
                if output.returncode == 0:
                    for line in output.stdout.strip().split('\n'):
                        if line.strip():
                            body.append(f"[{log_file['type']}] {line.strip()}")
        
        return body
        
    except Exception as e:
        logger.error(f'获取初始日志内容失败: {e}')
        return [f"获取日志内容失败: {e}"]
