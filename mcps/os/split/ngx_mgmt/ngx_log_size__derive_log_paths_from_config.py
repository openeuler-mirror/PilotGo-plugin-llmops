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


def derive_log_paths_from_config(config_content: str) -> List[str]:
    """
    从配置文件中提取日志路径
    
    参数:
        config_content: 配置文件内容
        
    返回:
        list: 日志路径列表
    """
    log_paths = []
    
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 提取access_log路径
        access_log_pattern = r'access_log\s+([^;\s]+)'  # NOSONAR
        access_matches = re.findall(access_log_pattern, body)  # NOSONAR
        for match in access_matches:
            filepath = match.strip().strip('"\'')
            if not filepath.startswith('syslog:') and filepath != 'off':
                log_paths.append(filepath)
        
        # 提取error_log路径
        error_log_pattern = r'error_log\s+([^;\s]+)'  # NOSONAR
        error_matches = re.findall(error_log_pattern, body)  # NOSONAR
        for match in error_matches:
            filepath = match.strip().strip('"\'')
            if not filepath.startswith('stderr') and filepath != 'syslog:':
                log_paths.append(filepath)
        
        # 解析include文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        for include in includes:
            include_path = include.strip().strip('"\'')
            if '*' in include_path:
                # 处理通配符
                import glob
                included_files = glob.glob(include_path)
                for included_file in included_files:
                    if os.filepath.exists(included_file):
                        included_content = load_nginx_config(included_file)
                        included_paths = derive_log_paths_from_config(included_content)
                        log_paths.extend(included_paths)
            else:
                if os.filepath.exists(include_path):
                    included_content = load_nginx_config(include_path)
                    included_paths = derive_log_paths_from_config(included_content)
                    log_paths.extend(included_paths)
        
    except Exception as e:
        logger.error(f"提取日志路径失败: {e}")
    
    return sorted(set(log_paths))  # 去重
