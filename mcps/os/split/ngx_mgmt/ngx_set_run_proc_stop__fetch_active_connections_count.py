#!/usr/bin/env python3

import subprocess
import psutil
import os
import time
import logging
from datetime import datetime
import signal

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')


def fetch_active_connections_count():
    """
    获取当前活动连接数

    Returns:
        int: 活动连接数
    """
    try:
        # 尝试通过nginx -s status获取连接数
        try:
            output = subprocess.run(
                ['nginx', '-s', 'status'],
                capture_output=True, text=True, timeout=10
            )
            if output.returncode == 0:
                # 解析输出中的连接数
                lines = output.stdout.split('\n')
                for line in lines:
                    if 'active connections' in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.isdigit():
                                return int(part)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        # 备选方案：通过netstat统计连接数
        try:
            output = subprocess.run(
                ['netstat', '-an', '|', 'grep', ':80', '|', 'grep', 'ESTABLISHED', '|', 'wc', '-l'],
                shell=True, capture_output=True, text=True
            )
            if output.returncode == 0:
                return int(output.stdout.strip())
        except Exception:
            pass

        # 如果无法获取准确连接数，返回0（假设没有连接）
        return 0

    except Exception as e:
        logger.error(f"获取活动连接数失败: {e}")
        return 0
