#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
import os
import re
import subprocess
import sys

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_redis_config_dir() -> Optional[str]:
    """
    获取Redis配置目录

    返回:
        Redis配置目录，如果找不到则返回None
    """
    try:
        cfg_out = execute_redis_command('CONFIG GET dir')
        if cfg_out:
            lines = cfg_out.split('\n')
            if len(lines) >= 2 and lines[1]:
                return lines[1]
    except Exception as e:
        logger.warning(f"获取Redis配置目录失败: {e}")

    return None
def locate_backup_files(config_dir: str,
                     config_file: str,
                     backup_patterns: List[str] = None) -> Dict[str, Any]:
    """
    查找配置备份文件

    参数:
        config_dir: 配置目录
        config_file: 配置文件名
        backup_patterns: 备份文件匹配模式列表

    返回:
        备份文件信息字典
    """
    output = {
        'backups': [],
        'total_backups': 0,
        'message': '查找配置备份文件'
    }

    if backup_patterns is None:
        backup_patterns = [
            r'.*\.bak$',
            r'.*\.backup$',
            r'.*\.old$',
            r'.*\.save$',
            r'.*\.conf\.\d+$',
            r'.*\.conf\.\d{4}-\d{2}-\d{2}.*$',
            r'.*\.conf\.\d{8}.*$',
            r'.*backup_\d+.*$',
            r'.*_\d{8}_\d{6}.*$'
        ]

    try:
        if not os.path.exists(config_dir):
            output['message'] = f'配置目录不存在: {config_dir}'
            return output

        config_basename = os.path.basename(config_file)
        config_name = os.path.splitext(config_basename)[0]

        for filename in os.listdir(config_dir):
            filepath = os.path.join(config_dir, filename)

            if not os.path.isfile(filepath):
                continue

            is_backup = False
            matched_pattern = None

            for pattern in backup_patterns:
                if re.match(pattern, filename, re.IGNORECASE):  # NOSONAR
                    is_backup = True
                    matched_pattern = pattern
                    break

            if is_backup or (config_name in filename.lower() and filename != config_basename):
                backup_info = {
                    'filename': filename,
                    'filepath': filepath,
                    'size': os.path.getsize(filepath),
                    'modified_time': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    'created_time': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                    'is_compressed': filename.endswith('.gz') or filename.endswith('.zip'),
                    'matched_pattern': matched_pattern
                }

                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{8}|\d{14})', filename)  # NOSONAR
                if timestamp_match:
                    backup_info['timestamp'] = timestamp_match.group(1)

                ver_match = re.search(r'(v\d+|version\d+)', filename, re.IGNORECASE)  # NOSONAR
                if ver_match:
                    backup_info['version'] = ver_match.group(1)

                note_match = re.search(r'(before|after|pre|post|manual|auto)', filename, re.IGNORECASE)  # NOSONAR
                if note_match:
                    backup_info['note'] = note_match.group(1)

                output['backups'].append(backup_info)

        output['backups'].sort(key=lambda x: x['modified_time'], reverse=True)
        output['total_backups'] = len(output['backups'])
        output['message'] = f'找到 {output["total_backups"]} 个配置备份文件'

    except Exception as e:
        output['message'] = f'查找配置备份文件时发生异常: {str(e)}'
        logger.error(output['message'])

    return output
def fetch_backup_list(config_dir: Optional[str] = None,
                   config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    获取配置备份文件列表

    参数:
        config_dir: 配置目录
        config_file: 配置文件路径

    返回:
        备份文件列表信息字典
    """
    output = {
        'backups': [],
        'total_backups': 0,
        'storage_path': '',
        'message': '获取配置备份文件列表'
    }

    try:
        if not config_dir:
            config_dir = fetch_redis_config_dir()
            if not config_dir:
                output['message'] = '无法获取Redis配置目录'
                return output

        if not config_file:
            config_file = get_redis_config_file()
            if not config_file:
                output['message'] = '无法获取Redis配置文件路径'
                return output

        backup_result = locate_backup_files(config_dir, config_file)

        output['backups'] = backup_result['backups']
        output['total_backups'] = backup_result['total_backups']
        output['storage_path'] = config_dir
        output['message'] = backup_result['message']

    except Exception as e:
        output['message'] = f'获取配置备份文件列表时发生异常: {str(e)}'
        logger.error(output['message'])

    return output
def fetch_backup_summary(config_dir: Optional[str] = None,
                      config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    获取配置备份摘要信息

    参数:
        config_dir: 配置目录
        config_file: 配置文件路径

    返回:
        备份摘要信息字典
    """
    output = {
        'total_backups': 0,
        'total_size': 0,
        'oldest_backup': None,
        'newest_backup': None,
        'compressed_backups': 0,
        'message': '获取配置备份摘要'
    }

    try:
        backup_list = fetch_backup_list(config_dir, config_file)

        if not backup_list['total_backups']:
            output['message'] = '没有找到配置备份文件'
            return output

        backups = backup_list['backups']
        output['total_backups'] = len(backups)

        total_size = sum(b['size'] for b in backups)
        output['total_size'] = total_size

        if backups:
            output['oldest_backup'] = backups[-1]
            output['newest_backup'] = backups[0]

        output['compressed_backups'] = sum(1 for b in backups if b['is_compressed'])

        output['message'] = f'备份摘要: 总数 {output["total_backups"]}, 总大小 {total_size} 字节, 压缩 {output["compressed_backups"]}'

    except Exception as e:
        output['message'] = f'获取配置备份摘要时发生异常: {str(e)}'
        logger.error(output['message'])

    return output
