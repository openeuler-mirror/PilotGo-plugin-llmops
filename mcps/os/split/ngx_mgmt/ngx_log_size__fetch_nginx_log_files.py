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


def fetch_nginx_log_files() -> List[Dict[str, Any]]:
    """
    获取Nginx所有日志文件路径
    
    返回:
        list: 日志文件信息列表
    """
    log_files = []
    
    try:
        # 获取Nginx配置文件路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            logger.warning("无法找到Nginx配置文件")
            return log_files
        
        # 解析配置文件获取日志路径
        config_content = load_nginx_config(cfg_filepath)
        log_paths = derive_log_paths_from_config(config_content)
        
        # 获取实际存在的日志文件
        for log_path in log_paths:
            if os.filepath.exists(log_path):
                log_files.extend(fetch_log_files_from_path(log_path))
            else:
                # 尝试查找可能的日志文件
                log_files.extend(locate_possible_log_files(log_path))
        
        # 添加常见的Nginx日志文件
        common_logs = fetch_common_nginx_logs()
        for common_log in common_logs:
            if os.filepath.exists(common_log['filepath']):
                if not any(log['filepath'] == common_log['filepath'] for log in log_files):
                    log_files.append(common_log)
        
        # 去重
        unique_logs = []
        seen_paths = set()
        for log_file in log_files:
            if log_file['filepath'] not in seen_paths:
                unique_logs.append(log_file)
                seen_paths.add(log_file['filepath'])
        
        return unique_logs
        
    except Exception as e:
        logger.error(f"获取Nginx日志文件失败: {e}")
        return []
