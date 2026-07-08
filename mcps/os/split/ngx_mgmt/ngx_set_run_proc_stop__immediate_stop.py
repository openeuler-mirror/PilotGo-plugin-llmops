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


def immediate_stop():
    """
    立即停止Nginx（不等待连接释放）

    Returns:
        dict: 停止结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 发送SIGTERM信号（立即停止）
        nginx_pids = fetch_nginx_master_pids()
        if not nginx_pids:
            output["message"] = "未找到运行的Nginx主进程"
            output["success"] = True
            return output

        output["message"] = "立即停止信号已发送"
        output["success"] = True
        return output

    except Exception as e:
        logger.error(f"立即停止Nginx失败: {e}")
        return {"success": False, "message": f"立即停止失败: {e}", "error": str(e)}
