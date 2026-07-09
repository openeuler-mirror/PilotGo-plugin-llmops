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
logger = logging.getLogger('net_bridge')

def fetch_net_bridge():
    """
    采集网桥配置（网桥接口/桥接网卡/IP配置/STP状态/转发规则）

    返回:
        格式化的网桥配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 网桥配置 ===')

        # 采集网桥接口列表
        bridge_interfaces = fetch_bridge_interfaces()
        if bridge_interfaces:
            for interface in bridge_interfaces:
                output.append(f'\n网桥接口: {interface}')

                # 采集网桥详细信息
                bridge_info = fetch_bridge_info(interface)
                if bridge_info:
                    for key, value in bridge_info.items():
                        output.append(f"  {key}: {value}")

                # 采集桥接网卡
                bridge_ports = fetch_bridge_ports(interface)
                if bridge_ports:
                    output.append('  桥接网卡:')
                    for port in bridge_ports:
                        output.append(f"    - {port}")
                else:
                    output.append('  桥接网卡: 无')

                # 采集网桥IP配置
                bridge_ip = fetch_bridge_ip(interface)
                if bridge_ip:
                    output.append('  IP配置:')
                    for key, value in bridge_ip.items():
                        output.append(f"    {key}: {value}")

                # 采集网桥STP状态
                bridge_stp = fetch_bridge_stp(interface)
                if bridge_stp:
                    output.append('  STP状态:')
                    for key, value in bridge_stp.items():
                        output.append(f"    {key}: {value}")

                # 采集网桥状态
                bridge_status = fetch_bridge_status(interface)
                if bridge_status:
                    output.append('  状态:')
                    for key, value in bridge_status.items():
                        output.append(f"    {key}: {value}")
        else:
            output.append('\n网桥接口: 无')

        # 采集网桥统计
        bridge_stats = fetch_bridge_stats(bridge_interfaces)
        if bridge_stats:
            output.append('\n网桥统计:')
            for key, value in bridge_stats.items():
                output.append(f"  {key}: {value}")

        # 检查网桥状态
        bridge_checks = verify_bridge_status(bridge_interfaces)
        if bridge_checks:
            output.append('\n网桥状态检查:')
            for check in bridge_checks:
                output.append(f"  - {check}")

        # 分析网桥配置
        bridge_analysis = examine_bridge_config(bridge_interfaces)
        if bridge_analysis:
            output.append('\n网桥配置分析:')
            for analysis in bridge_analysis:
                output.append(f"  - {analysis}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取网桥配置失败: {e}')
        return f'获取网桥配置失败: {e}'
def fetch_bridge_interfaces():
    """
    获取网桥接口列表
    """
    interfaces = []

    try:
        # 使用brctl命令获取网桥列表
        output = subprocess.run(['brctl', 'show'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过标题行
                if line:
                    parts = line.split()
                    if parts:
                        interface = parts[0]
                        interfaces.append(interface)
        else:
            # 如果brctl不可用，检查/sys/class/net目录
            net_dir = '/sys/class/net'
            if os.path.exists(net_dir):
                for interface in os.listdir(net_dir):
                    bridge_dir = os.path.join(net_dir, interface, 'bridge')
                    if os.path.exists(bridge_dir):
                        interfaces.append(interface)

    except Exception as e:
        logger.error(f'获取网桥接口失败: {e}')

    return interfaces
