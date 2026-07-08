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
