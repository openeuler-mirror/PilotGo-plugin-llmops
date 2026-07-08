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


def wait_for_process_stop(timeout=60):
    """
    等待进程完全停止

    Args:
        timeout: 超时时间（秒）

    Returns:
        dict: 等待结果
    """
    try:
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次

        while time.time() - start_time < timeout:
            nginx_pids = fetch_nginx_all_pids()
            if not nginx_pids:
                return {"success": True, "message": "所有Nginx进程已停止"}

            time.sleep(check_interval)

        # 超时处理
        remaining_pids = fetch_nginx_all_pids()
        return {
            "success": False,
            "message": f"等待进程停止超时，剩余进程PID: {remaining_pids}",
            "error": "进程停止超时"
        }

    except Exception as e:
        logger.error(f"等待进程停止失败: {e}")
        return {"success": False, "message": f"等待进程停止失败: {e}", "error": str(e)}
