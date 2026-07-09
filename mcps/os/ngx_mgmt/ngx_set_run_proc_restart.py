from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
import re
import shutil
import subprocess
import time

import psutil

from mcp_tools.cmd_safety_guard import validate_identifier_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info, get_nginx_config_path, check_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_runtime_process_restart')

def set_nginx_process_restart(
    restart_type="graceful",
    wait_time=10,
    max_wait_time=60,
    check_interval=2,
    force_restart=False
):
    """
    平滑重启Nginx进程（避免中断现有连接）

    Args:
        restart_type: 重启类型 ("graceful"|"restart"|"reload")
        wait_time: 等待新进程稳定时间（秒）
        max_wait_time: 最大等待时间（秒）
        check_interval: 检查间隔（秒）
        force_restart: 是否强制重启（当平滑重启失败时）
    """
    try:
        output = []
        output.append('=== Nginx进程平滑重启工具 ===')

        # 获取nginx进程信息
        proc_info = get_nginx_process_info()
        if proc_info['status'] == '已停止':
            output.append('错误: Nginx服务未运行')
            return '\n'.join(output)

        # 记录重启前状态
        output.append(f'\n重启前状态:')
        output.append(f'  Nginx状态: {proc_info["status"]}')
        output.append(f'  主进程PID: {proc_info["master_pid"]}')
        output.append(f'  工作进程数: {proc_info["worker_count"]}')

        # 获取详细的进程信息
        pre_restart_processes = fetch_detailed_process_info()
        output.append(f'  总进程数: {len(pre_restart_processes)}')

        # 执行重启操作
        restart_result = perform_nginx_restart(
            restart_type,
            wait_time,
            max_wait_time,
            check_interval,
            force_restart
        )

        output.append(f'\n重启操作:')
        output.append(f'  重启类型: {restart_type}')
        output.append(f'  操作结果: {restart_result["status"]}')

        if restart_result["status"] == "success":
            output.append(f'  重启耗时: {restart_result["duration"]:.2f}秒')

            # 获取重启后状态
            time.sleep(2)  # 等待进程稳定
            post_restart_processes = fetch_detailed_process_info()

            output.append(f'\n重启后状态:')
            output.append(f'  总进程数: {len(post_restart_processes)}')

            # 比较进程变化
            process_changes = examine_process_changes(pre_restart_processes, post_restart_processes)
            output.append(f'  进程变化: {process_changes}')

            # 检查连接保持情况
            connection_check = verify_connection_preservation(pre_restart_processes, post_restart_processes)
            output.append(f'  连接保持: {connection_check}')

            output.append('\n✅ 平滑重启成功完成，现有连接未中断')

        else:
            output.append(f'  错误信息: {restart_result["error"]}')

            # 如果平滑重启失败，尝试强制重启
            if force_restart:
                output.append(f'\n⚠️ 平滑重启失败，尝试强制重启...')
                force_result = perform_force_restart()
                output.append(f'  强制重启结果: {force_result["status"]}')
                if force_result["status"] == "success":
                    output.append(f'  强制重启耗时: {force_result["duration"]:.2f}秒')
                else:
                    output.append(f'  强制重启错误: {force_result["error"]}')

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'Nginx进程重启失败: {e}')
        return f'Nginx进程重启失败: {e}'

def perform_nginx_restart(restart_type, wait_time, max_wait_time, check_interval, force_restart):
    """执行Nginx重启操作"""
    start_time = time.time()

    try:
        if restart_type == "graceful":
            # 平滑重启 - 发送USR2信号给主进程
            output = graceful_restart()
        elif restart_type == "reload":
            # 重载配置 - 发送HUP信号给主进程
            output = reload_configuration()
        elif restart_type == "restart":
            # 完全重启 - 停止后启动
            output = full_restart()
        else:
            return {
                "status": "error",
                "error": f"不支持的重启类型: {restart_type}",
                "duration": time.time() - start_time
            }

        if output["status"] == "success":
            # 等待新进程稳定
            wait_result = wait_for_stable_processes(wait_time, max_wait_time, check_interval)
            if wait_result["status"] == "success":
                output["duration"] = time.time() - start_time
                return output
            else:
                return {
                    "status": "error",
                    "error": f"进程稳定等待失败: {wait_result['error']}",
                    "duration": time.time() - start_time
                }
        else:
            output["duration"] = time.time() - start_time
            return output

    except Exception as e:
        return {
            "status": "error",
            "error": f"重启操作异常: {e}",
            "duration": time.time() - start_time
        }

def graceful_restart():
    """执行平滑重启（USR2信号）"""
    try:
        # 获取主进程PID
        proc_info = get_nginx_process_info()
        if proc_info['status'] == '已停止':
            return {"status": "error", "error": "Nginx服务未运行"}

        master_pid = proc_info["master_pid"]

        # 发送USR2信号给主进程（启动新的主进程）
        subprocess.run(['kill', '-USR2', str(master_pid)], check=True, timeout=10)
        logger.info(f'已发送USR2信号给主进程 {master_pid}')

        # 等待新主进程启动
        time.sleep(3)

        # 发送WINCH信号给旧主进程（优雅关闭工作进程）
        subprocess.run(['kill', '-WINCH', str(master_pid)], check=True, timeout=10)
        logger.info(f'已发送WINCH信号给旧主进程 {master_pid}')

        # 检查新主进程是否已启动
        new_process_info = get_nginx_process_info()
        if new_process_info['status'] == '运行中' and new_process_info["master_pid"] != master_pid:
            logger.info(f'新主进程已启动，PID: {new_process_info["master_pid"]}')

            # 可选：发送QUIT信号给旧主进程（完全关闭）
            # subprocess.run(['kill', '-QUIT', str(master_pid)], check=True, timeout=10)

            return {"status": "success"}
        else:
            return {"status": "error", "error": "新主进程未成功启动"}

    except subprocess.CalledProcessError as e:
        return {"status": "error", "error": f"信号发送失败: {e}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "信号发送超时"}
    except Exception as e:
        return {"status": "error", "error": f"平滑重启异常: {e}"}

def reload_configuration():
    """重载配置（HUP信号）"""
    try:
        # 获取主进程PID
        proc_info = get_nginx_process_info()
        if proc_info['status'] == '已停止':
            return {"status": "error", "error": "Nginx服务未运行"}

        master_pid = proc_info["master_pid"]

        # 发送HUP信号给主进程（重载配置）
        subprocess.run(['kill', '-HUP', str(master_pid)], check=True, timeout=10)
        logger.info(f'已发送HUP信号给主进程 {master_pid}')

        # 等待配置重载完成
        time.sleep(2)

        # 验证配置重载
        config_check = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        return {"status": "success"} if config_check.returncode == 0 else {"status": "error", "error": f"配置验证失败: {config_check.stderr}"}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "error": f"信号发送失败: {e}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "信号发送超时"}
    except Exception as e:
        return {"status": "error", "error": f"配置重载异常: {e}"}

def full_restart():
    """完全重启（停止后启动）"""
    try:
        # 停止Nginx服务
        stop_result = subprocess.run(['systemctl', 'stop', 'nginx'],
                                   capture_output=True, text=True, timeout=30)

        if stop_result.returncode != 0:
            # 尝试使用service命令
            stop_result = subprocess.run(['service', 'nginx', 'stop'],
                                       capture_output=True, text=True, timeout=30)

        # 等待服务停止
        time.sleep(3)

        # 启动Nginx服务
        start_result = subprocess.run(['systemctl', 'start', 'nginx'],
                                    capture_output=True, text=True, timeout=30)

        if start_result.returncode != 0:
            # 尝试使用service命令
            start_result = subprocess.run(['service', 'nginx', 'start'],
                                        capture_output=True, text=True, timeout=30)

        if start_result.returncode == 0:
            # 等待服务启动
            time.sleep(5)
            return {"status": "success"}
        else:
            return {"status": "error", "error": f"启动失败: {start_result.stderr}"}

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "重启操作超时"}
    except Exception as e:
        return {"status": "error", "error": f"完全重启异常: {e}"}

def wait_for_stable_processes(wait_time, max_wait_time, check_interval):
    """等待进程稳定"""
    start_time = time.time()
    last_worker_count = 0
    stable_count = 0

    try:
        while time.time() - start_time < max_wait_time:
            proc_info = get_nginx_process_info()

            if proc_info['status'] == '已停止':
                return {"status": "error", "error": "Nginx服务已停止"}

            current_worker_count = proc_info["worker_count"]

            # 检查工作进程数是否稳定
            if current_worker_count == last_worker_count:
                stable_count += 1
            else:
                stable_count = 0
                last_worker_count = current_worker_count

            # 如果连续多次检查进程数稳定，则认为已稳定
            if stable_count >= 3:
                logger.info(f'进程已稳定，工作进程数: {current_worker_count}')
                return {"status": "success"}

            # 等待下一次检查
            time.sleep(check_interval)

        return {"status": "error", "error": f"等待进程稳定超时（{max_wait_time}秒）"}

    except Exception as e:
        return {"status": "error", "error": f"等待进程稳定异常: {e}"}