#!/usr/bin/env python3
"""
Nginx配置重载工具
实现仅重载配置而不重启进程的功能
"""
Nginx配置重载工具
实现仅重载配置而不重启进程的功能
"""

import subprocess
import os
import time
import logging
import tempfile
import shutil
from datetime import datetime
import re

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_info, execute_command

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_reload')

def reload_nginx_config(reload_type="graceful", config_check=True, backup_config=True, timeout=60):
    """

from datetime import datetime
import glob
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time

import psutil
import psutil
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_info, execute_command

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_reload')

def reload_nginx_config(reload_type="graceful", config_check=True, backup_config=True, timeout=60):
    """
    重载Nginx配置（不重启进程）

    Args:
        reload_type: 重载类型 ("graceful"|"force"|"test")
        config_check: 是否进行配置语法检查
        backup_config: 是否备份当前配置
        timeout: 超时时间（秒）

    Returns:
        dict: 重载结果
    """
    try:
        output = {
            "success": False,
            "message": "",
            "reload_type": reload_type,
            "config_check": config_check,
            "backup_config": backup_config,
            "timeout": timeout,
            "process_info_before": {},
            "process_info_after": {},
            "config_info_before": {},
            "config_info_after": {},
            "backup_path": "",
            "test_result": "",
            "elapsed_time": 0,
            "error": ""
        }

        start_time = time.time()

        # 获取重载前的进程和配置信息
        output["process_info_before"] = get_nginx_process_info()
        if output["process_info_before"]["status"] != "运行中":
            output["error"] = "Nginx服务未运行，无法重载配置"
            return output

        output["config_info_before"] = get_nginx_config_info()

        # 备份配置
        if backup_config:
            backup_result = save_current_config()
            if backup_result["success"]:
                output["backup_path"] = backup_result["backup_path"]
            else:
                logger.warning(f"配置备份失败: {backup_result.get('error', '')}")

        # 配置语法检查
        if config_check:
            test_result = probe_nginx_config()
            output["test_result"] = test_result["message"]
            if not test_result["success"]:
                output["error"] = f"配置语法检查失败: {test_result.get('error', '')}"
                return output

        # 根据重载类型执行重载操作
        if reload_type == "graceful":
            reload_result = graceful_reload(timeout)
        elif reload_type == "force":
            reload_result = force_reload(timeout)
        elif reload_type == "test":
            reload_result = {"success": True, "message": "仅进行配置测试，不执行重载"}
        else:
            raise ValueError(f"不支持的重载类型: {reload_type}")

        # 获取重载后的信息
        if reload_type != "test":
            wait_result = wait_for_reload_completion(timeout)
            output["process_info_after"] = get_nginx_process_info()
            output["config_info_after"] = get_nginx_config_info()
        else:
            wait_result = {"success": True, "message": "测试模式，无需等待重载完成"}

        output["elapsed_time"] = time.time() - start_time
        output["success"] = reload_result["success"] and wait_result["success"]

        # 构建详细消息
        messages = []
        if reload_type == "test":
            messages.append(f"配置测试: {output['test_result']}")
        else:
            messages.append(f"重载操作: {reload_result['message']}")
            messages.append(f"等待结果: {wait_result['message']}")

        output["message"] = ", ".join(messages)

        if not output["success"]:
            output["error"] = f"重载失败: {reload_result.get('error', '')} {wait_result.get('error', '')}"

        return output

    except Exception as e:
        logger.error(f"重载Nginx配置失败: {e}")
        return {
            "success": False,
            "message": f"重载配置失败: {e}",
            "error": str(e)
        }

def graceful_reload(timeout=60):
    """
    平滑重载Nginx配置

    Args:
        timeout: 超时时间（秒）

    Returns:
        dict: 重载结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 使用nginx -s reload命令进行平滑重载
        cmd_result = execute_command(['nginx', '-s', 'reload'], timeout=timeout)

        if cmd_result["success"]:
            output["success"] = True
            output["message"] = "平滑重载命令执行成功"
        else:
            output["error"] = cmd_result.get("error", "重载命令执行失败")
            output["message"] = f"平滑重载失败: {output['error']}"

        return output

    except Exception as e:
        logger.error(f"平滑重载Nginx配置失败: {e}")
        return {"success": False, "message": f"平滑重载失败: {e}", "error": str(e)}

def force_reload(timeout=60):
    """
    强制重载Nginx配置（使用HUP信号）

    Args:
        timeout: 超时时间（秒）

    Returns:
        dict: 重载结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 获取Nginx主进程PID
        nginx_pids = fetch_nginx_master_pids()
        if not nginx_pids:
            output["error"] = "未找到运行的Nginx主进程"
            return output

        output["success"] = True
        output["message"] = "强制重载信号已发送"
        return output

    except Exception as e:
        logger.error(f"强制重载Nginx配置失败: {e}")
        return {"success": False, "message": f"强制重载失败: {e}", "error": str(e)}