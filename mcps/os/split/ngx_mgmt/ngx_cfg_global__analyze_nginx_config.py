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


def analyze_nginx_config(config_file: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件，提取全局配置项

    参数:
        config_file: Nginx配置文件路径

    返回:
        包含所有全局配置项的字典
    """
    try:
        if not os.path.exists(config_file):
            return {'error': f'配置文件不存在: {config_file}'}

        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 初始化结果字典
        global_config = {
            'config_file': config_file,
            'global_directives': {},
            'events_directives': {},
            'http_directives': {},
            'includes': [],
            'parsing_errors': []
        }

        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR

        # 解析全局指令（不在任何块内的指令）
        global_pattern = r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+(.*?);'  # NOSONAR
        global_matches = re.findall(global_pattern, body, re.MULTILINE)  # NOSONAR

        for directive, value in global_matches:
            # 过滤掉块指令
            if directive not in ['events', 'http', 'server', 'location', 'upstream', 'mail']:
                global_config['global_directives'][directive] = value.strip()

        # 解析events块
        events_pattern = r'events\s*{(.*?)}'  # NOSONAR
        events_match = re.search(events_pattern, body, re.DOTALL)  # NOSONAR
        if events_match:
            events_content = events_match.group(1)
            events_directives = re.findall(global_pattern, events_content, re.MULTILINE)  # NOSONAR
            for directive, value in events_directives:
                global_config['events_directives'][directive] = value.strip()

        # 解析http块
        http_pattern = r'http\s*{(.*?)(?=\s*}\s*$)'  # NOSONAR
        http_match = re.search(http_pattern, body, re.DOTALL)  # NOSONAR
        if http_match:
            http_content = http_match.group(1)
            # 提取http块内的全局指令（不包括嵌套块）
            http_directives = re.findall(global_pattern, http_content, re.MULTILINE)  # NOSONAR
            for directive, value in http_directives:
                # 过滤掉嵌套块指令
                if directive not in ['server', 'location', 'upstream', 'map', 'geo', 'split_clients', 'perl', 'limit_conn_zone', 'limit_req_zone']:
                    global_config['http_directives'][directive] = value.strip()

        # 解析include指令
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        include_matches = re.findall(include_pattern, body)  # NOSONAR
        for include_path in include_matches:
            global_config['includes'].append(include_path.strip())

        return global_config

    except Exception as e:
        logger.error(f'解析Nginx配置文件失败: {e}')
        return {
            'error': f'解析配置文件失败: {e}',
            'config_file': config_file
        }
