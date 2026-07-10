#!/usr/bin/env python3
"""
Nginx日志导出工具
支持将指定过滤条件的日志导出为txt/csv/json格式，支持指定存储路径
"""

import os
import re
import json
import csv
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_export')

# 预定义的日志格式解析器
LOG_FORMAT_PARSERS = {
    'combined': r'^(\S+) - (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)"',
    'main': r'^(\S+) - (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+)',
    'custom': None  # 自定义格式需要动态解析
}

def verify_nginx_installation() -> Dict[str, Any]:
    """
    检查Nginx是否安装
    
    返回:
        dict: 包含安装状态和信息的字典
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        if output.returncode == 0:
            return {
                'installed': True,
                'version': output.stderr.strip() if output.stderr else 'Unknown',
                'suggestion': 'Nginx已正确安装'
            }
        else:
            return {
                'installed': False,
                'version': 'Unknown',
                'suggestion': '请先安装Nginx或检查PATH环境变量'
            }
    except Exception as e:
        return {
            'installed': False,
            'version': 'Unknown',
            'suggestion': f'检查Nginx安装失败: {e}'
        }

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
            # 解析配置文件路径
            config_match = re.search(r'nginx: the configuration file ([^\s]+)', output)  # NOSONAR
            if config_match:
                return config_match.group(1)
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None