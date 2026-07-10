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
