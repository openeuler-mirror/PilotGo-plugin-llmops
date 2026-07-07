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


def analyze_current_log_configs(body: str, cfg_filepath: str) -> Dict:
    """解析当前日志配置"""
    logs_info = {
        'access_logs': [],
        'error_logs': [],
        'include_files': []
    }

    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"analyze_current_log_configs: cfg_filepath 路径验证失败：{error_msg}")
            return logs_info

        # 解析主配置文件中的日志配置
        access_log_pattern = r'access_log\s+([^;]+);'  # NOSONAR
        error_log_pattern = r'error_log\s+([^;]+);'  # NOSONAR

        # 主配置文件中的日志配置
        access_matches = re.findall(access_log_pattern, body)  # NOSONAR
        error_matches = re.findall(error_log_pattern, body)  # NOSONAR

        for match in access_matches:
            logs_info['access_logs'].append({
                'path': match.strip(),
                'file': cfg_filepath,
                'type': 'main'
            })

        for match in error_matches:
            logs_info['error_logs'].append({
                'path': match.strip(),
                'file': cfg_filepath,
                'type': 'main'
            })

        # 解析 include 文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        include_matches = re.findall(include_pattern, body)  # NOSONAR

        config_dir = os.path.dirname(cfg_filepath)
        for include in include_matches:
            include_path = include.strip().strip('"\'').strip()
            if not os.path.isabs(include_path):
                include_path = os.path.join(config_dir, include_path)

            # 处理通配符
            if '*' in include_path:
                included_files = glob.glob(include_path)
                for file in included_files:
                    if os.path.isfile(file):
                        logs_info['include_files'].append(file)
            elif os.path.exists(include_path):
                if os.path.isfile(include_path):
                    logs_info['include_files'].append(include_path)
                elif os.path.isdir(include_path):
                    for file in os.listdir(include_path):
                        if file.endswith('.conf'):
                            logs_info['include_files'].append(os.path.join(include_path, file))

        # 解析include文件中的日志配置
        for include_file in logs_info['include_files']:
            try:
                include_content = Path(include_file).read_text(encoding='utf-8')

                include_access_matches = re.findall(access_log_pattern, include_content)  # NOSONAR
                include_error_matches = re.findall(error_log_pattern, include_content)  # NOSONAR

                for match in include_access_matches:
                    logs_info['access_logs'].append({
                        'path': match.strip(),
                        'file': include_file,
                        'type': 'include'
                    })

                for match in include_error_matches:
                    logs_info['error_logs'].append({
                        'path': match.strip(),
                        'file': include_file,
                        'type': 'include'
                    })

            except Exception as e:
                logger.warning(f'解析include文件失败 {include_file}: {e}')
                continue

        return logs_info

    except Exception as e:
        logger.error(f'解析日志配置失败: {e}')
        return logs_info
