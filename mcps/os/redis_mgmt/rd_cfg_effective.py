#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
import subprocess
import sys

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_config_line(line: str) -> Dict[str, Any]:
    """
    解析配置文件行

    参数:
        line: 配置文件行

    返回:
        解析后的配置行信息字典
    """
    output = {
        'raw_line': line,
        'is_comment': False,
        'is_empty': False,
        'is_directive': False,
        'directive': '',
        'val': '',
        'comment': ''
    }

    stripped_line = line.strip()

    if not stripped_line:
        output['is_empty'] = True
        return output

    if stripped_line.startswith('#'):
        output['is_comment'] = True
        output['comment'] = stripped_line[1:].strip()
        return output

    if stripped_line.startswith('include ') or stripped_line.startswith('include\t'):
        output['is_directive'] = True
        parts = stripped_line.split(None, 1)
        output['directive'] = parts[0]
        output['val'] = parts[1].strip() if len(parts) > 1 else ''
        return output

    if ' ' in stripped_line or '\t' in stripped_line:
        parts = stripped_line.split(None, 1)
        if parts:
            output['directive'] = parts[0]
            if len(parts) > 1:
                output['val'] = parts[1]

                if '#' in output['val']:
                    value_parts = output['val'].split('#', 1)
                    output['val'] = value_parts[0].strip()
                    output['comment'] = value_parts[1].strip()

    return output
def fetch_file_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    获取配置文件中的配置项

    参数:
        cfg_filepath: 配置文件路径

    返回:
        配置文件配置项信息字典
    """
    output = {
        'config': {},
        'total_items': 0,
        'message': '获取配置文件配置项'
    }

    try:
        lines = read_config_file(cfg_filepath)

        for line_num, line in enumerate(lines, 1):
            parsed_line = analyze_config_line(line.rstrip('\n'))

            if parsed_line['directive'] and not parsed_line['is_directive']:
                output['config'][parsed_line['directive']] = {
                    'val': parsed_line['val'],
                    'line_number': line_num,
                    'source': 'file',
                    'is_commented': False
                }

        output['total_items'] = len(output['config'])
        output['message'] = f'配置文件中找到 {output["total_items"]} 个配置项'

    except Exception as e:
        output['message'] = f'获取配置文件配置项时发生异常: {e}'
        logger.error(output['message'])

    return output
def fetch_runtime_config() -> Dict[str, Any]:
    """
    获取运行时配置项

    返回:
        运行时配置项信息字典
    """
    output = {
        'config': {},
        'total_items': 0,
        'message': '获取运行时配置项'
    }

    try:
        cfg_out = execute_redis_command('CONFIG GET *')
        if cfg_out:
            lines = cfg_out.split('\n')

            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    key = lines[i]
                    val = lines[i + 1]
                    output['config'][key] = {
                        'val': val,
                        'source': 'runtime',
                        'is_dynamic': True
                    }

            output['total_items'] = len(output['config'])
            output['message'] = f'运行时配置中找到 {output["total_items"]} 个配置项'

    except Exception as e:
        output['message'] = f'获取运行时配置项时发生异常: {e}'
        logger.error(output['message'])

    return output
