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


def locate_access_log_paths():
    """查找访问日志文件路径"""
    log_paths = []
    try:
        # 从Nginx配置中查找访问日志路径
        output = subprocess.run(['nginx', '-T'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode in [0, 1]:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 查找access_log指令
            access_log_matches = re.findall(r'access_log\s+([^\s;]+)', output, re.IGNORECASE)  # NOSONAR
            for match in access_log_matches:
                if not match.endswith('off'):
                    log_paths.append(match)

        # 默认路径
        default_paths = [
            '/var/log/nginx/access.log',
            '/var/log/nginx/access.log.1',
            '/var/log/nginx/localhost.access.log',
            '/usr/local/nginx/logs/access.log',
            '/etc/nginx/logs/access.log'
        ]

        for path in default_paths:
            if path not in log_paths and os.path.exists(path):
                log_paths.append(path)

        return log_paths

    except Exception as e:
        logger.error(f'查找访问日志路径失败: {e}')
        return ['/var/log/nginx/access.log']
