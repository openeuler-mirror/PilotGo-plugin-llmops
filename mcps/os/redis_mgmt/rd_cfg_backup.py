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
