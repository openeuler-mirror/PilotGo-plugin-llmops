#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_clear')


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
