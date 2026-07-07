#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_include')


def fetch_config_include_status() -> Dict:
    """
    获取Nginx配置include状态

    返回:
        dict: 包含include状态信息的字典
    """
    try:
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            return {
                'error': 'Nginx未安装',
                'suggestion': nginx_status.get('suggestion', '请安装Nginx')
            }

        # 获取主配置文件路径
        cfg_state = get_nginx_config_info()
        main_config_path = cfg_state.get('config_file', '/etc/nginx/nginx.conf')

        # 检查主配置文件是否存在
        if not os.path.exists(main_config_path):
            return {
                'error': f'主配置文件不存在: {main_config_path}',
                'suggestion': '请检查Nginx配置文件路径'
            }

        # 获取嵌套include信息
        include_tree = fetch_nested_includes(main_config_path)

        # 统计信息
        stats = {
            'total_include_directives': 0,
            'total_included_files': 0,
            'existing_files': 0,
            'missing_files': 0,
            'unreadable_files': 0
        }

        # 递归统计
        def count_includes(node):
            if 'includes' in node:
                stats['total_include_directives'] += len(node['includes'])

                for include in node['includes']:
                    if 'resolved_files' in include:
                        stats['total_included_files'] += len(include['resolved_files'])

                        for file_info in include['resolved_files']:
                            if file_info.get('exists', False):
                                stats['existing_files'] += 1
                                if not file_info.get('is_readable', False):
                                    stats['unreadable_files'] += 1
                            else:
                                stats['missing_files'] += 1

                    # 递归处理嵌套include
                    for file_info in include.get('resolved_files', []):
                        if file_info.get('exists', False) and 'nested_includes' in file_info:
                            count_includes(file_info['nested_includes'])

        count_includes(include_tree)

        # 检查配置语法
        config_test_result = subprocess.run(
            ['nginx', '-t'],
            capture_output=True,
            text=True,
            stderr=subprocess.STDOUT
        )

        config_status = {
            'syntax_valid': config_test_result.returncode == 0,
            'output': config_test_result.stdout.strip()
        }

        return {
            'main_config': main_config_path,
            'include_tree': include_tree,
            'statistics': stats,
            'config_status': config_status
        }

    except Exception as e:
        logger.error(f'获取配置include状态失败: {e}')
        return {
            'error': f'获取配置include状态失败: {e}'
        }
