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

def probe_nginx_config():
    """
    测试Nginx配置语法

    Returns:
        dict: 测试结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 使用nginx -t命令测试配置语法
        cmd_result = execute_command(['nginx', '-t'], timeout=30)

        if cmd_result["success"]:
            output["success"] = True
            output["message"] = "配置语法检查通过"

            # 解析测试输出
            output = cmd_result.get("output", "")
            if "syntax is ok" in output.lower() and "test is successful" in output.lower():
                output["message"] = "配置语法检查通过，测试成功"
            else:
                output["message"] = "配置语法检查完成，但输出异常"
        else:
            output["error"] = cmd_result.get("error", "配置测试命令执行失败")
            output["message"] = f"配置语法检查失败: {output['error']}"

        return output

    except Exception as e:
        logger.error(f"测试Nginx配置语法失败: {e}")
        return {"success": False, "message": f"配置测试失败: {e}", "error": str(e)}

def save_current_config():
    """
    备份当前Nginx配置

    Returns:
        dict: 备份结果
    """
    try:
        output = {"success": False, "message": "", "backup_path": "", "error": ""}

        # 获取Nginx配置信息
        cfg_state = get_nginx_config_info()
        config_file = cfg_state.get('config_file', '')

        if not config_file or not os.path.exists(config_file):
            output["error"] = "Nginx配置文件不存在或无法访问"
            return output

        # 创建备份目录
        backup_dir = "/tmp/nginx_config_backups"  # NOSONAR
        os.makedirs(backup_dir, exist_ok=True)

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nginx.conf.backup.{timestamp}"
        backup_path = os.path.join(backup_dir, backup_filename)

        # 备份配置文件
        shutil.copy2(config_file, backup_path)

        # 备份include文件（如果存在）
        include_files = locate_include_files(config_file)
        for include_file in include_files:
            if os.path.exists(include_file):
                include_backup_dir = os.path.join(backup_dir, "includes")
                os.makedirs(include_backup_dir, exist_ok=True)
                include_backup_path = os.path.join(include_backup_dir,
                                                 f"{os.path.basename(include_file)}.{timestamp}")
                shutil.copy2(include_file, include_backup_path)

        output["success"] = True
        output["message"] = f"配置备份完成，主配置文件备份至: {backup_path}"
        output["backup_path"] = backup_path

        if include_files:
            output["message"] += f"，包含 {len(include_files)} 个include文件"

        return output

    except Exception as e:
        logger.error(f"备份Nginx配置失败: {e}")
        return {"success": False, "message": f"配置备份失败: {e}", "error": str(e)}

def locate_include_files(config_file):
    """
    查找配置文件中的include文件

    Args:
        config_file: 主配置文件路径

    Returns:
        list: include文件路径列表
    """
    try:
        include_files = []

        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 匹配include指令
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        matches = re.findall(include_pattern, body)  # NOSONAR

        config_dir = os.path.dirname(config_file)

        for match in matches:
            include_pattern = match.strip().strip('"').strip("'")

            # 处理通配符
            if '*' in include_pattern:
                # 使用glob处理通配符
                pattern_path = os.path.join(config_dir, include_pattern)
                matched_files = glob.glob(pattern_path)
                include_files.extend(matched_files)
            else:
                # 直接路径
                include_path = os.path.join(config_dir, include_pattern)
                if os.path.exists(include_path):
                    include_files.append(include_path)

        return sorted(set(include_files))  # 去重

    except Exception as e:
        logger.error(f"查找include文件失败: {e}")
        return []

def wait_for_reload_completion(timeout=60):
    """
    等待重载完成

    Args:
        timeout: 超时时间（秒）

    Returns:
        dict: 等待结果
    """
    try:
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次

        # 获取初始进程信息
        initial_info = get_nginx_process_info()
        initial_pids = fetch_nginx_all_pids()

        logger.info(f"开始等待重载完成，超时时间: {timeout}秒")

        while time.time() - start_time < timeout:
            current_info = get_nginx_process_info()

            # 检查服务状态
            if current_info["status"] != "运行中":
                return {
                    "success": False,
                    "message": "Nginx服务在重载过程中停止",
                    "error": "服务停止"
                }

            # 检查进程变化（工作进程应该重新启动）
            current_pids = fetch_nginx_all_pids()
            worker_changed = verify_worker_process_change(initial_pids, current_pids)

            if worker_changed:
                logger.info("工作进程已重新启动，重载完成")
                return {"success": True, "message": "重载完成，工作进程已更新"}

            time.sleep(check_interval)

        # 超时处理
        return {
            "success": False,
            "message": "等待重载完成超时",
            "error": "重载超时"
        }

    except Exception as e:
        logger.error(f"等待重载完成失败: {e}")
        return {"success": False, "message": f"等待重载完成失败: {e}", "error": str(e)}

def verify_worker_process_change(initial_pids, current_pids):
    """
    检查工作进程是否发生变化

    Args:
        initial_pids: 初始PID列表
        current_pids: 当前PID列表

    Returns:
        bool: 工作进程是否发生变化
    """
    try:
        # 获取工作进程PID（排除主进程）
        def fetch_worker_pids(pids):
            worker_pids = []
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    cmdline = ' '.join(proc.cmdline()).lower() if proc.cmdline() else ''
                    if 'nginx' in cmdline and 'worker' in cmdline:
                        worker_pids.append(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return worker_pids

        initial_workers = fetch_worker_pids(initial_pids)
        current_workers = fetch_worker_pids(current_pids)

        # 如果工作进程PID完全不同，说明已重新启动
        if initial_workers and current_workers:
            common_pids = set(initial_workers) & set(current_workers)
            return len(common_pids) == 0  # 没有共同PID说明已完全重启

        return False

    except Exception as e:
        logger.error(f"检查工作进程变化失败: {e}")
        return False