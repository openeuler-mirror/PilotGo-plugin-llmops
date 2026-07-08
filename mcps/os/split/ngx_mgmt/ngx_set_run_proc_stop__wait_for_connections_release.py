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


def wait_for_connections_release(timeout=300):
    """
    等待所有连接释放

    Args:
        timeout: 超时时间（秒）

    Returns:
        bool: 是否成功等待连接释放
    """
    try:
        start_time = time.time()
        check_interval = 5  # 每5秒检查一次

        logger.info(f"开始等待连接释放，超时时间: {timeout}秒")

        while time.time() - start_time < timeout:
            current_connections = fetch_active_connections_count()

            if current_connections == 0:
                logger.info("所有连接已释放")
                return True

            # 显示当前连接数
            if int(time.time() - start_time) % 30 == 0:  # 每30秒显示一次
                logger.info(f"当前活动连接数: {current_connections}")

            time.sleep(check_interval)

        # 超时处理
        remaining_connections = fetch_active_connections_count()
        logger.warning(f"等待连接释放超时，剩余连接数: {remaining_connections}")
        return False

    except Exception as e:
        logger.error(f"等待连接释放失败: {e}")
        return False
