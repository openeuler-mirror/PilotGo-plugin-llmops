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
def fetch_interface_bandwidth(interface):
    """
    获取网卡带宽信息
    """
    bandwidth = {}

    try:
        # 安全校验：验证网卡名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'网卡名称不合法：{error_msg}')
            bandwidth['最大带宽'] = '未知'
            return bandwidth

        # 尝试使用 ethtool 获取网卡最大带宽
        output = subprocess.run(['ethtool', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if 'Speed:' in line:
                    speed = line.split(':')[1].strip()
                    bandwidth['最大带宽'] = speed
                    break
        else:
            # 如果 ethtool 不可用，使用默认值
            bandwidth['最大带宽'] = '未知'

    except Exception as e:
        logger.error(f'获取网卡带宽失败：{e}')
        bandwidth['最大带宽'] = '未知'

    return bandwidth
def fetch_interface_rate(interface):
    """
    获取网卡速率
    """
    rate = {}

    try:
        # 读取/proc/net/dev获取初始统计
        initial_stats = fetch_dev_stats(interface)
        if initial_stats:
            # 等待1秒
            time.sleep(1)

            # 读取/proc/net/dev获取结束统计
            final_stats = fetch_dev_stats(interface)
            if final_stats:
                # 计算接收速率
                rx_bytes = final_stats['rx_bytes'] - initial_stats['rx_bytes']
                rx_rate = rx_bytes * 8 / 1024 / 1024  # 转换为Mbps
                rate['接收速率'] = f"{rx_rate:.2f} Mbps"

                # 计算发送速率
                tx_bytes = final_stats['tx_bytes'] - initial_stats['tx_bytes']
                tx_rate = tx_bytes * 8 / 1024 / 1024  # 转换为Mbps
                rate['发送速率'] = f"{tx_rate:.2f} Mbps"

                # 计算总速率
                total_rate = rx_rate + tx_rate
                rate['总速率'] = f"{total_rate:.2f} Mbps"

    except Exception as e:
        logger.error(f'获取网卡速率失败: {e}')

    return rate
def fetch_dev_stats(interface):
    """
    从/proc/net/dev获取网卡统计
    """
    stats = {}

    try:
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()

            for line in lines[2:]:
                if interface in line:
                    parts = line.split(':')[1].strip().split()
                    if len(parts) >= 16:
                        stats['rx_bytes'] = int(parts[0])
                        stats['rx_packets'] = int(parts[1])
                        stats['rx_errors'] = int(parts[2])
                        stats['rx_dropped'] = int(parts[3])
                        stats['tx_bytes'] = int(parts[8])
                        stats['tx_packets'] = int(parts[9])
                        stats['tx_errors'] = int(parts[10])
                        stats['tx_dropped'] = int(parts[11])
                    break

    except Exception as e:
        logger.error(f'获取网卡统计失败: {e}')

    return stats
def fetch_interface_stats(interface):
    """
    获取网卡统计信息
    """
    stats = {}

    try:
        dev_stats = fetch_dev_stats(interface)
        if dev_stats:
            stats['接收字节数'] = f"{dev_stats['rx_bytes']} 字节"
            stats['接收数据包数'] = dev_stats['rx_packets']
            stats['接收错误数'] = dev_stats['rx_errors']
            stats['接收丢弃数'] = dev_stats['rx_dropped']
            stats['发送字节数'] = f"{dev_stats['tx_bytes']} 字节"
            stats['发送数据包数'] = dev_stats['tx_packets']
            stats['发送错误数'] = dev_stats['tx_errors']
            stats['发送丢弃数'] = dev_stats['tx_dropped']

    except Exception as e:
        logger.error(f'获取网卡统计失败: {e}')

    return stats
def fetch_total_bandwidth(interfaces):
    """
    获取总带宽信息
    """
    total = {}

    try:
        total_rx_bytes = 0
        total_tx_bytes = 0
        total_rate = 0

        for interface in interfaces:
            # 获取速率
            rate_info = fetch_interface_rate(interface)
            if rate_info:
                # 提取速率值
                if '总速率' in rate_info:
                    rate_str = rate_info['总速率']
                    rate = float(rate_str.split()[0])
                    total_rate += rate

            # 获取统计
            stats_info = fetch_interface_stats(interface)
            if stats_info:
                if '接收字节数' in stats_info:
                    rx_bytes = int(stats_info['接收字节数'].split()[0].replace(',', ''))
                    total_rx_bytes += rx_bytes
                if '发送字节数' in stats_info:
                    tx_bytes = int(stats_info['发送字节数'].split()[0].replace(',', ''))
                    total_tx_bytes += tx_bytes

        total['总速率'] = f"{total_rate:.2f} Mbps"
        total['总接收字节数'] = f"{total_rx_bytes} 字节"
        total['总发送字节数'] = f"{total_tx_bytes} 字节"
        total['总传输字节数'] = f"{total_rx_bytes + total_tx_bytes} 字节"

    except Exception as e:
        logger.error(f'获取总带宽失败: {e}')

    return total
