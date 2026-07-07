#!/usr/bin/env python3

from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import re
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_global')


def fetch_global_config() -> Dict[str, Any]:
    """
    获取Nginx全局配置项

    返回:
        包含所有全局配置项及其说明的字典
    """
    try:
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            return {
                'error': 'Nginx未安装',
                'suggestion': nginx_status.get('suggestion', '请安装Nginx')
            }

        # 获取配置文件路径
        cfg_state = get_nginx_config_info()
        config_file = cfg_state.get('config_file', 'Unknown')

        if config_file == 'Unknown':
            return {
                'error': '无法确定Nginx配置文件路径',
                'suggestion': '请检查Nginx安装和配置'
            }

        # 解析配置文件
        parsed_config = analyze_nginx_config(config_file)

        if 'error' in parsed_config:
            return parsed_config

        # 构建结果，包含配置项及其说明
        output = {
            'config_file': config_file,
            'config_test': cfg_state.get('config_test', 'Unknown'),
            'global_directives': {},
            'events_directives': {},
            'http_directives': {},
            'includes': parsed_config.get('includes', []),
            'summary': {
                'total_global_directives': len(parsed_config.get('global_directives', {})),
                'total_events_directives': len(parsed_config.get('events_directives', {})),
                'total_http_directives': len(parsed_config.get('http_directives', {})),
                'total_includes': len(parsed_config.get('includes', []))
            }
        }

        # 添加全局指令及其说明
        for directive, value in parsed_config.get('global_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get(directive, '自定义配置项')
            output['global_directives'][directive] = {
                'value': value,
                'description': description
            }

        # 添加events指令及其说明
        for directive, value in parsed_config.get('events_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get('events', {}).get(directive, '自定义配置项')
            output['events_directives'][directive] = {
                'value': value,
                'description': description
            }

        # 添加http指令及其说明
        for directive, value in parsed_config.get('http_directives', {}).items():
            description = GLOBAL_DIRECTIVES.get('http', {}).get(directive, '自定义配置项')
            output['http_directives'][directive] = {
                'value': value,
                'description': description
            }

        return output

    except Exception as e:
        logger.error(f'获取Nginx全局配置失败: {e}')
        return {
            'error': f'获取全局配置失败: {e}'
        }
