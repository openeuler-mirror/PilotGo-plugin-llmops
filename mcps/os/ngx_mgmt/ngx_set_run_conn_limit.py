#!/usr/bin/env python3
"""
Nginx运行时连接限制管理工具
设置最大连接数、单IP最大连接数、连接队列长度等连接限制参数
"""

import os
import re
import json
import logging
import subprocess
import shutil
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, fetch_nginx_config_path, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_connect_limit')

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