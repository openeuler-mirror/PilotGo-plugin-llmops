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


def fetch_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    获取文件详细信息
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 文件信息字典
    """
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_file_info: file_path 路径验证失败：{error_msg}")
            return None
        
        if not os.filepath.exists(file_path):
            return None
        
        stat_info = os.stat(file_path)
        
        # 文件大小
        size_bytes = stat_info.st_size
        size_human = render_size(size_bytes)
        
        # 最后修改时间
        mtime = datetime.fromtimestamp(stat_info.st_mtime)
        mtime_str = mtime.strftime('%Y-%m-%d %H:%M:%S')
        mtime_relative = render_time(datetime.now() - mtime)
        
        # 文件类型
        file_type = 'regular'
        if os.filepath.islink(file_path):
            file_type = 'symlink'
            try:
                target = os.readlink(file_path)
                if os.filepath.exists(target):
                    file_type = 'symlink_valid'
            except Exception:
                file_type = 'symlink_broken'
        
        # 磁盘使用情况
        disk_usage = fetch_disk_usage(file_path)
        
        file_info = {
            'filepath': file_path,
            'size_bytes': size_bytes,
            'size_human': size_human,
            'modified_time': mtime_str,
            'modified_relative': mtime_relative,
            'file_type': file_type,
            'inode': stat_info.st_ino,
            'permissions': oct(stat_info.st_mode)[-3:],
            'disk_usage': disk_usage
        }
        
        # 添加文件分类
        file_info.update(classify_log_file(file_path))
        
        return file_info
        
    except Exception as e:
        logger.error(f"获取文件信息失败 {file_path}: {e}")
        return None
