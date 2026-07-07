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


def verify_nginx_running():
    """检查Nginx是否正在运行"""
    try:
        output = subprocess.run(['pgrep', '-f', 'nginx'], capture_output=True, text=True)
        if output.returncode == 0:
            pids = output.stdout.strip().split('\n')
            master_pids = []
            for pid in pids:
                try:
                    proc = psutil.Process(int(pid))
                    if 'master' in ' '.join(proc.cmdline()).lower():
                        master_pids.append(pid)
                except Exception:
                    continue

            return {'running': True, 'message': 'Nginx主进程正在运行', 'master_pids': master_pids} if master_pids else {'running': True, 'message': 'Nginx工作进程正在运行', 'worker_pids': pids}
        else:
            return {'running': False, 'message': 'Nginx服务未运行'}
    except Exception as e:
        logger.error(f'检查Nginx运行状态失败: {e}')
        return {'running': False, 'message': f'检查失败: {e}'}
