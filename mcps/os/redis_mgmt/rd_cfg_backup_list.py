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
