#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import glob
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_path_modify')


def fetch_nginx_config_path() -> Optional[str]:
    """获取Nginx配置文件路径"""
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0 or output.returncode == 1:  # 允许配置错误但仍获取路径
            output = output.stdout if output.stdout else output.stderr
            config_match = re.search(r'file ([^\s]+) test', output)  # NOSONAR
            if config_match:
                return config_match.group(1)

        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/usr/local/etc/nginx/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    except Exception as e:
        logger.error(f'获取Nginx配置路径失败: {e}')
        return None
