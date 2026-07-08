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


def fetch_nginx_log_size() -> str:
    """
    获取Nginx日志文件大小统计信息
    
    返回:
        str: JSON格式的日志文件大小统计信息
    """
    try:
        # 获取所有日志文件
        log_files = fetch_nginx_log_files()
        
        if not log_files:
            return json.dumps({
                'status': 'warning',
                'message': '未找到Nginx日志文件',
                'suggestion': '请检查Nginx是否正常运行且配置了日志文件',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 计算总体统计信息
        total_stats = compute_total_stats(log_files)
        
        # 构建结果
        output = {
            'status': 'success',
            'total_stats': total_stats,
            'log_files': log_files,
            'timestamp': datetime.now().isoformat(),
            'file_count': len(log_files)
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取Nginx日志大小失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'获取日志大小失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)
