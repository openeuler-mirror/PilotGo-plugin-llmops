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
logger = logging.getLogger('net_bond')

def fetch_net_bond():
    """
    采集网卡绑定（bond接口/绑定模式/成员网卡/IP配置/运行状态/故障转移）

    返回:
        格式化的网卡绑定信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 网卡绑定 ===')

        # 采集bond接口列表
        bond_interfaces = fetch_bond_interfaces()
        if bond_interfaces:
            for interface in bond_interfaces:
                output.append(f'\nbond接口: {interface}')

                # 采集bond详细信息
                bond_info = fetch_bond_info(interface)
                if bond_info:
                    for key, value in bond_info.items():
                        output.append(f"  {key}: {value}")

                # 采集成员网卡
                bond_slaves = fetch_bond_slaves(interface)
                if bond_slaves:
                    output.append('  成员网卡:')
                    for slave in bond_slaves:
                        slave_status = fetch_slave_status(slave, interface)
                        status_str = f"({slave_status})" if slave_status else ""
                        output.append(f"    - {slave} {status_str}")
                else:
                    output.append('  成员网卡: 无')

                # 采集bond IP配置
                bond_ip = fetch_bond_ip(interface)
                if bond_ip:
                    output.append('  IP配置:')
                    for key, value in bond_ip.items():
                        output.append(f"    {key}: {value}")

                # 采集bond状态
                bond_status = fetch_bond_status(interface)
                if bond_status:
                    output.append('  状态:')
                    for key, value in bond_status.items():
                        output.append(f"    {key}: {value}")

                # 采集bond统计
                bond_stats = fetch_bond_stats(interface)
                if bond_stats:
                    output.append('  统计:')
                    for key, value in bond_stats.items():
                        output.append(f"    {key}: {value}")
        else:
            output.append('\nbond接口: 无')

        # 采集bond统计
        bond_stats = fetch_bond_stats_summary(bond_interfaces)
        if bond_stats:
            output.append('\nbond统计:')
            for key, value in bond_stats.items():
                output.append(f"  {key}: {value}")

        # 检查bond状态
        bond_checks = verify_bond_status(bond_interfaces)
        if bond_checks:
            output.append('\nbond状态检查:')
            for check in bond_checks:
                output.append(f"  - {check}")

        # 分析bond配置
        bond_analysis = examine_bond_config(bond_interfaces)
        if bond_analysis:
            output.append('\nbond配置分析:')
            for analysis in bond_analysis:
                output.append(f"  - {analysis}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取网卡绑定失败: {e}')
        return f'获取网卡绑定失败: {e}'
def fetch_bond_interfaces():
    """
    获取bond接口列表
    """
    interfaces = []

    try:
        # 检查/sys/class/net目录
        net_dir = '/sys/class/net'
        if os.path.exists(net_dir):
            for interface in os.listdir(net_dir):
                bond_dir = os.path.join(net_dir, interface, 'bonding')
                if os.path.exists(bond_dir):
                    interfaces.append(interface)

        # 使用ip命令获取bond接口
        output = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if 'bond' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        interface = parts[1].strip().split('@')[0]
                        if interface not in interfaces:
                            interfaces.append(interface)

    except Exception as e:
        logger.error(f'获取bond接口失败: {e}')

    return interfaces
def fetch_bond_info(interface):
    """
    获取 bond 详细信息
    """
    bond_info = {}

    try:
        # 安全校验：验证接口名称参数
        is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
        if not is_valid:
            logger.error(f'接口名称不合法：{error_msg}')
            return bond_info

        # 检查/sys/class/net目录
        bond_dir = f'/sys/class/net/{interface}/bonding'
        if os.path.exists(bond_dir):
            # 获取绑定模式
            mode_file = os.path.join(bond_dir, 'mode')
            if os.path.exists(mode_file):
                with open(mode_file, 'r') as f:
                    mode = f.read().strip()
                    bond_info['绑定模式'] = mode

            # 获取活跃网卡
            active_file = os.path.join(bond_dir, 'active_slave')
            if os.path.exists(active_file):
                with open(active_file, 'r') as f:
                    active = f.read().strip()
                    if active:
                        bond_info['活跃网卡'] = active
                    else:
                        bond_info['活跃网卡'] = '无'

            # 获取 MII 监控间隔
            mii_file = os.path.join(bond_dir, 'miimon')
            if os.path.exists(mii_file):
                with open(mii_file, 'r') as f:
                    miimon = f.read().strip()
                    bond_info['MII 监控间隔'] = f"{miimon} ms"

            # 获取 ARP 监控间隔
            arp_file = os.path.join(bond_dir, 'arp_interval')
            if os.path.exists(arp_file):
                with open(arp_file, 'r') as f:
                    arp_interval = f.read().strip()
                    if arp_interval != '0':
                        bond_info['ARP 监控间隔'] = f"{arp_interval} ms"

            # 获取故障转移延迟
            failover_file = os.path.join(bond_dir, 'fail_over_mac')
            if os.path.exists(failover_file):
                with open(failover_file, 'r') as f:
                    failover = f.read().strip()
                    bond_info['故障转移 MAC'] = failover

    except Exception as e:
        logger.error(f'获取 bond 信息失败：{e}')

    return bond_info
