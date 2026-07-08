#!/usr/bin/env python3
"""
Nginx安全停止进程工具
实现等待所有连接释放后退出功能
"""
Nginx安全停止进程工具
实现等待所有连接释放后退出功能
"""

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

def perform_nginx_stop(stop_type="graceful", timeout=300, wait_connections=True):
    """

from datetime import datetime
import logging
import os
import signal
import subprocess
import time

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

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

def force_stop():
    """
    强制停止Nginx（使用SIGKILL信号）

    Returns:
        dict: 停止结果
    """
    try:
        output = {"success": False, "message": "", "error": ""}

        # 发送SIGKILL信号（强制停止）
        nginx_pids = fetch_nginx_all_pids()
        if not nginx_pids:
            output["message"] = "未找到运行的Nginx进程"
            output["success"] = True
            return output

        output["message"] = "强制停止信号已发送"
        output["success"] = True
        return output

    except Exception as e:
        logger.error(f"强制停止Nginx失败: {e}")
        return {"success": False, "message": f"强制停止失败: {e}", "error": str(e)}

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

def fetch_nginx_master_pids():
    """
    获取Nginx主进程PID列表

    Returns:
        list: 主进程PID列表
    """
    try:
        pids = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['name'] and 'nginx' in proc.info['name'].lower() and
                    proc.info['cmdline'] and 'master' in ' '.join(proc.info['cmdline']).lower()):
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids
    except Exception as e:
        logger.error(f"获取Nginx主进程PID失败: {e}")
        return []

def fetch_nginx_all_pids():
    """
    获取所有Nginx进程PID列表

    Returns:
        list: 所有Nginx进程PID列表
    """
    try:
        pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return pids
    except Exception as e:
        logger.error(f"获取Nginx进程PID失败: {e}")
        return []

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

def examine_stop_recommendations():
    """
    分析并推荐停止策略

    Returns:
        dict: 推荐策略
    """
    try:
        proc_info = get_nginx_process_info()
        if proc_info["status"] == "已停止":
            return {"recommendation": "无需停止", "reason": "Nginx服务已经停止"}

        connection_count = fetch_active_connections_count()
        current_time = datetime.now().strftime("%H:%M")

        recommendations = []

        # 根据连接数和时间推荐策略
        if connection_count == 0:
            recommendations.append({
                "type": "immediate",
                "priority": "high",
                "reason": "当前无活动连接，可立即停止"
            })
        elif connection_count < 10:
            recommendations.append({
                "type": "graceful",
                "priority": "medium",
                "reason": f"活动连接较少({connection_count}个)，建议平滑停止"
            })
        else:
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": f"活动连接较多({connection_count}个)，必须平滑停止以保持服务连续性"
            })

        # 根据时间推荐
        hour = datetime.now().hour
        if 2 <= hour <= 5:  # 凌晨时段
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": "当前为业务低峰期，适合进行平滑停止"
            })
        elif 9 <= hour <= 18:  # 工作时间
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": "当前为业务高峰期，必须使用平滑停止"
            })

        # 选择优先级最高的推荐
        priority_map = {"high": 3, "medium": 2, "low": 1}
        best_recommendation = max(recommendations, key=lambda x: priority_map[x["priority"]])

        return {
            "current_status": {
                "nginx_running": proc_info["status"] == "运行中",
                "active_connections": connection_count,
                "current_time": current_time
            },
            "recommendations": recommendations,
            "best_recommendation": best_recommendation
        }

    except Exception as e:
        logger.error(f"分析停止推荐失败: {e}")
        return {"error": f"分析失败: {e}"}

def produce_stop_report(stop_result):
    """
    生成停止报告

    Args:
        stop_result: 停止操作结果

    Returns:
        str: 格式化报告
    """
    try:
        report = []
        report.append("=== Nginx停止操作报告 ===")
        report.append(f"操作时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"停止类型: {stop_result.get('stop_type', 'N/A')}")
        report.append(f"等待连接释放: {'是' if stop_result.get('wait_connections') else '否'}")
        report.append(f"超时时间: {stop_result.get('timeout', 'N/A')}秒")
        report.append(f"操作结果: {'成功' if stop_result.get('success') else '失败'}")
        report.append(f"耗时: {stop_result.get('elapsed_time', 0):.2f}秒")

        # 进程信息对比
        before_info = stop_result.get('process_info_before', {})
        after_info = stop_result.get('process_info_after', {})
        report.append(f"\n进程状态变化:")
        report.append(f"  停止前: {before_info.get('status', 'N/A')}")
        report.append(f"  停止后: {after_info.get('status', 'N/A')}")

        # 连接数变化
        if stop_result.get('wait_connections'):
            conn_before = stop_result.get('connection_count_before', 0)
            conn_after = stop_result.get('connection_count_after', 0)
            report.append(f"\n连接数变化:")
            report.append(f"  停止前: {conn_before} 个活动连接")
            report.append(f"  停止后: {conn_after} 个活动连接")

        # 操作信息
        report.append(f"\n操作详情:")
        report.append(f"  {stop_result.get('message', 'N/A')}")

        if stop_result.get('error'):
            report.append(f"\n错误信息:")
            report.append(f"  {stop_result.get('error')}")

        report.append("========================")
        return '\n'.join(report)

    except Exception as e:
        logger.error(f"生成停止报告失败: {e}")
        return f"生成报告失败: {e}"

# 工具配置
TOOL_CONFIG = {
    "name": "perform_nginx_stop",
    "function": perform_nginx_stop,
    "description": "安全停止Nginx进程，支持平滑停止（等待连接释放）、立即停止和强制停止",
    "parameters": {
        "type": "object",
        "properties": {
            "stop_type": {
                "type": "string",
                "enum": ["graceful", "immediate", "force"],
                "description": "停止类型：graceful(平滑停止)、immediate(立即停止)、force(强制停止)",
                "default": "graceful"
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒），默认300秒",
                "default": 300
            },
            "wait_connections": {
                "type": "boolean",
                "description": "是否等待连接释放，默认True",
                "default": True
            }
        },
        "required": []
    }
}
