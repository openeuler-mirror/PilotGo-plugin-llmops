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


def reload_nginx_config() -> Dict:
    """重载Nginx配置"""
    try:
        # 尝试平滑重载
        output = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)

        if output.returncode == 0:
            return {
                'success': True,
                'method': 'reload',
                'message': '配置重载成功'
            }
        else:
            # 如果平滑重载失败，尝试重启
            logger.warning('平滑重载失败，尝试重启Nginx')
            restart_result = subprocess.run(['systemctl', 'restart', 'nginx'], capture_output=True, text=True)

            if restart_result.returncode == 0:
                return {
                    'success': True,
                    'method': 'restart',
                    'message': 'Nginx重启成功'
                }
            else:
                return {
                    'success': False,
                    'method': 'both',
                    'message': '重载和重启都失败',
                    'reload_error': output.stderr,
                    'restart_error': restart_result.stderr
                }

    except Exception as e:
        logger.error(f'重载Nginx配置失败: {e}')
        return {
            'success': False,
            'method': 'error',
            'message': f'重载失败: {e}'
        }
