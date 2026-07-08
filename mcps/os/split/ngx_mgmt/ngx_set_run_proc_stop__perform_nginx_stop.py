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


def perform_nginx_stop(stop_type="graceful", timeout=300, wait_connections=True):
    """
    执行Nginx停止操作

    Args:
        stop_type: 停止类型 ("graceful"|"immediate"|"force")
        timeout: 超时时间（秒）
        wait_connections: 是否等待连接释放

    Returns:
        dict: 停止结果
    """
    try:
        output = {
            "success": False,
            "message": "",
            "stop_type": stop_type,
            "timeout": timeout,
            "wait_connections": wait_connections,
            "process_info_before": {},
            "process_info_after": {},
            "connection_count_before": 0,
            "connection_count_after": 0,
            "elapsed_time": 0,
            "error": ""
        }

        start_time = time.time()

        # 获取停止前的进程信息
        output["process_info_before"] = get_nginx_process_info()
        if output["process_info_before"]["status"] == "已停止":
            output["message"] = "Nginx服务已经停止"
            output["success"] = True
            return output

        # 获取停止前的连接数
        if wait_connections:
            output["connection_count_before"] = fetch_active_connections_count()

        # 根据停止类型执行不同的停止操作
        if stop_type == "graceful":
            stop_result = graceful_stop(timeout, wait_connections)
        elif stop_type == "immediate":
            stop_result = immediate_stop()
        elif stop_type == "force":
            stop_result = force_stop()
        else:
            raise ValueError(f"不支持的停止类型: {stop_type}")

        # 等待进程完全停止
        wait_result = wait_for_process_stop(timeout)

        # 获取停止后的信息
        output["process_info_after"] = get_nginx_process_info()
        if wait_connections:
            output["connection_count_after"] = fetch_active_connections_count()

        output["elapsed_time"] = time.time() - start_time
        output["success"] = stop_result["success"] and wait_result["success"]
        output["message"] = f"停止操作: {stop_result['message']}, 等待结果: {wait_result['message']}"

        if not output["success"]:
            output["error"] = f"停止失败: {stop_result.get('error', '')} {wait_result.get('error', '')}"

        return output

    except Exception as e:
        logger.error(f"执行Nginx停止操作失败: {e}")
        return {
            "success": False,
            "message": f"执行停止操作失败: {e}",
            "error": str(e)
        }
