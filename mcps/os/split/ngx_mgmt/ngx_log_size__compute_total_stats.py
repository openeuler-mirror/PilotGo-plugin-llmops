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


def compute_total_stats(log_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算总体统计信息
    
    参数:
        log_files: 日志文件列表
        
    返回:
        dict: 总体统计信息
    """
    stats = {
        'total_files': len(log_files),
        'total_size_bytes': 0,
        'total_size_human': '0 B',
        'oldest_file': None,
        'newest_file': None,
        'by_type': {},
        'by_directory': {}
    }
    
    try:
        # 计算总大小
        total_bytes = sum(log['size_bytes'] for log in log_files)
        stats['total_size_bytes'] = total_bytes
        stats['total_size_human'] = render_time(total_bytes)
        
        # 按类型统计
        for log_file in log_files:
            log_type = log_file['log_type']
            if log_type not in stats['by_type']:
                stats['by_type'][log_type] = {
                    'count': 0,
                    'total_size_bytes': 0,
                    'total_size_human': '0 B'
                }
            
            stats['by_type'][log_type]['count'] += 1
            stats['by_type'][log_type]['total_size_bytes'] += log_file['size_bytes']
            stats['by_type'][log_type]['total_size_human'] = render_time(
                stats['by_type'][log_type]['total_size_bytes']
            )
        
        # 按目录统计
        for log_file in log_files:
            dir_path = os.filepath.dirname(log_file['filepath'])
            if dir_path not in stats['by_directory']:
                stats['by_directory'][dir_path] = {
                    'count': 0,
                    'total_size_bytes': 0,
                    'total_size_human': '0 B'
                }
            
            stats['by_directory'][dir_path]['count'] += 1
            stats['by_directory'][dir_path]['total_size_bytes'] += log_file['size_bytes']
            stats['by_directory'][dir_path]['total_size_human'] = render_time(
                stats['by_directory'][dir_path]['total_size_bytes']
            )
        
        # 找到最旧和最新的文件
        if log_files:
            sorted_by_time = sorted(log_files, key=lambda x: x['modified_time'])
            stats['oldest_file'] = sorted_by_time[0]
            stats['newest_file'] = sorted_by_time[-1]
        
    except Exception as e:
        logger.error(f"计算统计信息失败: {e}")
    
    return stats
