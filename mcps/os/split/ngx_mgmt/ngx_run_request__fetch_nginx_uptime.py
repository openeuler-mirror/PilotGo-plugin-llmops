#!/usr/bin/env python3

from datetime import datetime
from typing import Dict, Optional, List
import json
import logging
import os
import re
import subprocess
import time

import psutil
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_request')


def fetch_nginx_uptime():
    """获取Nginx运行时间（秒）"""
    try:
        # 获取master进程的启动时间
        for proc in psutil.process_iter(['pid', 'name', 'create_time']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.cmdline()) if hasattr(proc, 'cmdline') else ''
                    if 'master' in cmdline.lower():
                        create_time = proc.info.get('create_time')
                        if create_time:
                            return int(time.time() - create_time)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return 0
    except Exception as e:
        logger.error(f'获取Nginx运行时间失败: {e}')
        return 0
