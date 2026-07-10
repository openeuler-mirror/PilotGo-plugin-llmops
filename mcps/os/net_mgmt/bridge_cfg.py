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
def fetch_bridge_info(interface):
    """
    获取网桥详细信息
    """
    bridge_info = {}

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return bridge_info

        # 使用brctl命令获取网桥信息
        output = subprocess.run(['brctl', 'show', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    bridge_info['网桥ID'] = parts[1]
                    bridge_info['STP'] = parts[2]
                    bridge_info['转发延迟'] = parts[3]

        # 检查/sys/class/net目录获取MTU
        mtu_file = f'/sys/class/net/{interface}/mtu'
        if os.path.exists(mtu_file):
            with open(mtu_file, 'r') as f:
                mtu = f.read().strip()
                bridge_info['MTU'] = mtu

    except Exception as e:
        logger.error(f'获取网桥信息失败: {e}')

    return bridge_info
def fetch_bridge_ports(interface):
    """
    获取桥接网卡
    """
    ports = []

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return ports

        # 使用brctl命令获取桥接网卡
        output = subprocess.run(['brctl', 'show', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines[2:]:  # 跳过标题和网桥行
                if line:
                    parts = line.split()
                    if parts:
                        port = parts[0]
                        ports.append(port)
        else:
            # 如果brctl不可用，检查/sys/class/net目录
            ports_dir = f'/sys/class/net/{interface}/brif'
            if os.path.exists(ports_dir):
                for port in os.listdir(ports_dir):
                    ports.append(port)

    except Exception as e:
        logger.error(f'获取桥接网卡失败: {e}')

    return ports
def fetch_bridge_ip(interface):
    """
    获取网桥 IP配置
    """
    bridge_ip = {}

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return bridge_ip

        # 使用ip命令获取IP信息
        output = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if 'inet ' in line:
                    # 提取IPv4地址
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        bridge_ip['IPv4地址'] = parts[1]
                elif 'inet6 ' in line and 'fe80::' not in line:
                    # 提取IPv6地址
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        bridge_ip['IPv6地址'] = parts[1]

    except Exception as e:
        logger.error(f'获取网桥IP配置失败: {e}')

    return bridge_ip
def fetch_bridge_stp(interface):
    """
    获取网桥 STP状态
    """
    bridge_stp = {}

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return bridge_stp

        # 使用brctl命令获取STP状态
        output = subprocess.run(['brctl', 'show', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 3:
                    bridge_stp['STP状态'] = '启用' if parts[2] == 'yes' else '禁用'

        # 检查/sys/class/net目录获取STP状态
        stp_file = f'/sys/class/net/{interface}/bridge/stp_state'
        if os.path.exists(stp_file):
            with open(stp_file, 'r') as f:
                stp_state = f.read().strip()
                bridge_stp['STP状态'] = '启用' if stp_state == '1' else '禁用'

    except Exception as e:
        logger.error(f'获取网桥STP状态失败: {e}')

    return bridge_stp
def fetch_bridge_status(interface):
    """
    获取网桥状态
    """
    state = {}

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return state

        # 使用ip命令获取状态
        output = subprocess.run(['ip', 'link', 'show', interface], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if interface in line:
                    # 提取状态
                    if 'UP' in line:
                        state['状态'] = 'UP'
                    else:
                        state['状态'] = 'DOWN'
                    # 提取是否运行
                    if 'LOWER_UP' in line:
                        state['运行状态'] = '运行中'
                    else:
                        state['运行状态'] = '未运行'

    except Exception as e:
        logger.error(f'获取网桥状态失败: {e}')

    return state
def fetch_bridge_stats(bridge_interfaces):
    """
    获取网桥统计
    """
    stats = {}

    try:
        # 统计网桥数量
        stats['网桥接口数量'] = len(bridge_interfaces)

        # 统计桥接网卡总数
        total_ports = 0
        for interface in bridge_interfaces:
            ports = fetch_bridge_ports(interface)
            total_ports += len(ports)
        stats['桥接网卡总数'] = total_ports

        # 统计STP启用的网桥
        stp_enabled = 0
        for interface in bridge_interfaces:
            stp = fetch_bridge_stp(interface)
            if stp.get('STP状态') == '启用':
                stp_enabled += 1
        stats['STP启用的网桥数量'] = stp_enabled
        stats['STP禁用的网桥数量'] = len(bridge_interfaces) - stp_enabled

        # 统计UP状态的网桥
        up_count = 0
        for interface in bridge_interfaces:
            state = fetch_bridge_status(interface)
            if state.get('状态') == 'UP':
                up_count += 1
        stats['UP状态的网桥数量'] = up_count
        stats['DOWN状态的网桥数量'] = len(bridge_interfaces) - up_count

    except Exception as e:
        logger.error(f'获取网桥统计失败: {e}')

    return stats
def verify_bridge_status(bridge_interfaces):
    """
    检查网桥状态
    """
    checks = []

    try:
        for interface in bridge_interfaces:
            # 检查网桥状态
            state = fetch_bridge_status(interface)
            if state.get('状态') == 'DOWN':
                checks.append(f"网桥接口 {interface} 状态为DOWN")
            if state.get('运行状态') == '未运行':
                checks.append(f"网桥接口 {interface} 未运行")

            # 检查桥接网卡
            ports = fetch_bridge_ports(interface)
            if not ports:
                checks.append(f"网桥接口 {interface} 未配置桥接网卡")

            # 检查STP状态（对于多端口网桥）
            if len(ports) > 1:
                stp = fetch_bridge_stp(interface)
                if stp.get('STP状态') == '禁用':
                    checks.append(f"警告: 多端口网桥 {interface} 未启用STP")

    except Exception as e:
        logger.error(f'检查网桥状态失败: {e}')

    return checks
def examine_bridge_config(bridge_interfaces):
    """
    分析网桥配置
    """
    analysis = []

    try:
        # 检查网桥数量
        if len(bridge_interfaces) > 5:
            analysis.append(f"网桥数量较多 ({len(bridge_interfaces)} 个)")

        # 检查每个网桥的桥接网卡数量
        for interface in bridge_interfaces:
            ports = fetch_bridge_ports(interface)
            if len(ports) > 10:
                analysis.append(f"网桥 {interface} 桥接网卡数量较多 ({len(ports)} 个)")

        # 检查是否有重复的桥接网卡
        all_ports = []
        for interface in bridge_interfaces:
            ports = fetch_bridge_ports(interface)
            all_ports.extend(ports)

        # 检查重复
        seen_ports = set()
        duplicate_ports = set()
        for port in all_ports:
            if port in seen_ports:
                duplicate_ports.add(port)
            else:
                seen_ports.add(port)

        if duplicate_ports:
            analysis.append(f"警告: 发现重复的桥接网卡: {', '.join(duplicate_ports)}")

    except Exception as e:
        logger.error(f'分析网桥配置失败: {e}')

    return analysis

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_net_bridge",
    "function": fetch_net_bridge,
    "description": "采集网桥配置（网桥接口/桥接网卡/IP配置/STP状态/转发规则）",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
