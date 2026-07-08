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


def fetch_common_nginx_logs() -> List[Dict[str, Any]]:
    """
    获取常见的Nginx日志文件
    
    返回:
        list: 常见日志文件列表
    """
    common_logs = []
    common_paths = [
        '/var/log/nginx/access.log',
        '/var/log/nginx/error.log',
        '/usr/local/nginx/logs/access.log',
        '/usr/local/nginx/logs/error.log',
        '/opt/nginx/logs/access.log',
        '/opt/nginx/logs/error.log'
    ]
    
    for filepath in common_paths:
        if os.filepath.exists(filepath):
            file_info = fetch_file_info(filepath)
            if file_info:
                file_info['type'] = 'common_file'
                common_logs.append(file_info)
    
    return common_logs
