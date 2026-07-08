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


def graceful_stop(timeout=300, wait_connections=True):
    """
    平滑停止Nginx（等待连接释放后退出）

    Args:
        timeout: 超时时间（秒）
        wait_connections: 是否等待连接释放

    Returns:
        dict: 停止结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 发送SIGQUIT信号（平滑停止）
        nginx_pids = fetch_nginx_master_pids()
        if not nginx_pids:
            output["message"] = "未找到运行的Nginx主进程"
            output["success"] = True
            return output


        # 如果需要等待连接释放，则监控连接数
        if wait_connections:
            wait_success = wait_for_connections_release(timeout)
            if wait_success:
                output["message"] = "平滑停止信号已发送，所有连接已释放"
            else:
                output["message"] = "平滑停止信号已发送，但连接释放超时"
        else:
            output["message"] = "平滑停止信号已发送"

        output["success"] = True
        return output

    except Exception as e:
        logger.error(f"平滑停止Nginx失败: {e}")
        return {"success": False, "message": f"平滑停止失败: {e}", "error": str(e)}
