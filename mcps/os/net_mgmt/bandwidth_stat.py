#!/usr/bin/env python3

from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import logging
import os
import subprocess
import time

from mcp_tools.cmd_safety_guard import validate_identifier_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_bandwidth')

def fetch_net_bandwidth():
    """
    采集网卡带宽（网卡最大带宽/当前使用率/收发速率/峰值带宽）

    返回:
        格式化的网卡带宽信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 网卡带宽 ===')

        # 采集网卡列表
        network_interfaces = fetch_network_interfaces()
        if network_interfaces:
            for interface in network_interfaces:
                output.append(f'\n网卡: {interface}')

                # 采集网卡带宽信息
                bandwidth_info = fetch_interface_bandwidth(interface)
                if bandwidth_info:
                    for key, value in bandwidth_info.items():
                        output.append(f"  {key}: {value}")

                # 采集网卡速率
                interface_rate = fetch_interface_rate(interface)
                if interface_rate:
                    output.append('  速率:')
                    for key, value in interface_rate.items():
                        output.append(f"    {key}: {value}")

                # 采集网卡统计
                interface_stats = fetch_interface_stats(interface)
                if interface_stats:
                    output.append('  统计:')
                    for key, value in interface_stats.items():
                        output.append(f"    {key}: {value}")
        else:
            output.append('\n网卡: 无')

        # 采集总带宽信息
        total_bandwidth = fetch_total_bandwidth(network_interfaces)
        if total_bandwidth:
            output.append('\n总带宽信息:')
            for key, value in total_bandwidth.items():
                output.append(f"  {key}: {value}")

        # 检查带宽状态
        bandwidth_status = verify_bandwidth_status(network_interfaces)
        if bandwidth_status:
            output.append('\n带宽状态检查:')
            for state in bandwidth_status:
                output.append(f"  - {state}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取网卡带宽失败: {e}')
        return f'获取网卡带宽失败: {e}'
def fetch_network_interfaces():
    """
    获取网络接口列表
    """
    interfaces = []

    try:
        # 读取/proc/net/dev
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()

            for line in lines[2:]:  # 跳过标题行
                if ':' in line:
                    interface = line.split(':')[0].strip()
                    # 排除回环接口和虚拟接口
                    if interface != 'lo' and not interface.startswith('veth') and not interface.startswith('docker'):
                        interfaces.append(interface)

    except Exception as e:
        logger.error(f'获取网络接口失败: {e}')

    return interfaces
