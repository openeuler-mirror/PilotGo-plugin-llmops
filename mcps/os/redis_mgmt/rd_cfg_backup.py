#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any
import json
import logging
import os
import shutil
import subprocess
import sys

from .rd_shared import *
import gzip

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
def produce_backup_filename(cfg_filepath: str,
                           note: Optional[str] = None,
                           timestamp: Optional[datetime] = None) -> str:
    """
    生成备份文件名

    参数:
        cfg_filepath: 原配置文件路径
        note: 版本备注
        timestamp: 时间戳，如果为None则使用当前时间

    返回:
        备份文件名
    """
    timestamp = datetime.now() if timestamp is None else timestamp
    config_basename = os.path.basename(cfg_filepath)
    config_name = os.path.splitext(config_basename)[0]

    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')

    backup_filename = f"{config_name}_backup_{timestamp_str}_{note}.conf" if note else f"{config_name}_backup_{timestamp_str}.conf"
    return backup_filename
def save_config_file(cfg_filepath: str,
                      backup_path: Optional[str] = None,
                      note: Optional[str] = None,
                      compress: bool = False) -> Dict[str, Any]:
    """
    备份配置文件

    参数:
        cfg_filepath: 配置文件路径
        backup_path: 备份文件路径，如果为None则自动生成
        note: 版本备注
        compress: 是否压缩备份文件

    返回:
        备份结果信息字典
    """
    output = {
        'success': False,
        'source_path': cfg_filepath,
        'backup_path': '',
        'size': 0,
        'compressed': compress,
        'note': note,
        'timestamp': datetime.now().isoformat(),
        'message': ''
    }

    try:
        if not os.path.exists(cfg_filepath):
            output['message'] = f'配置文件不存在: {cfg_filepath}'
            return output

        if not backup_path:
            config_dir = os.path.dirname(cfg_filepath)
            backup_filename = produce_backup_filename(cfg_filepath, note)
            backup_path = os.path.join(config_dir, backup_filename)

        backup_dir = os.path.dirname(backup_path)
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir, exist_ok=True)

        if compress:
            backup_path += '.gz'
            with open(cfg_filepath, 'rb') as f_in:
                with open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            with open(backup_path, 'rb') as f_in:
                with gzip.open(backup_path + '.tmp', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(backup_path)
            os.rename(backup_path + '.tmp', backup_path)
        else:
            shutil.copy2(cfg_filepath, backup_path)

        output['backup_path'] = backup_path
        output['size'] = os.path.getsize(backup_path)
        output['success'] = True
        output['message'] = f'配置文件已备份到: {backup_path}'

    except Exception as e:
        output['message'] = f'备份配置文件时发生异常: {e}'
        logger.error(output['message'])

    return output
