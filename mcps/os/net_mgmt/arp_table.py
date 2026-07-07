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
logger = logging.getLogger('net_arptable')

def fetch_net_arptable(interface=None):
    """
    采集 ARP 表（ARP 缓存/IP-MAC映射/静态ARP/过期时间/接口）

    参数:
        interface: 网络接口名称，如 "eth0"

    返回:
        格式化的ARP 表信息字符串
    """
    try:
        # 验证接口名称参数
        if interface is not None:
            validate_identifier_param(interface, "网络接口名称")

        # 基本信息
        output = []
        output.append('=== ARP 表 ===')

        # 采集ARP表
        arp_entries = fetch_arp_table(interface)
        if arp_entries:
            # 分类显示ARP条目
            static_entries = [entry for entry in arp_entries if entry.get('type') == 'static']
            dynamic_entries = [entry for entry in arp_entries if entry.get('type') == 'dynamic']

            if static_entries:
                output.append('\n静态ARP条目:')
                for entry in static_entries:
                    display_arp_entry(output, entry)

            if dynamic_entries:
                output.append('\n动态ARP条目:')
                for entry in dynamic_entries:
                    display_arp_entry(output, entry)
        else:
            output.append('ARP表为空')

        # 采集ARP表统计信息
        arp_stats = fetch_arp_stats(arp_entries)
        if arp_stats:
            output.append('\nARP表统计:')
            for key, value in arp_stats.items():
                output.append(f"  {key}: {value}")

        # 采集ARP缓存配置
        arp_config = fetch_arp_cache_config()
        if arp_config:
            output.append('\nARP缓存配置:')
            for key, value in arp_config.items():
                output.append(f"  {key}: {value}")

        # 采集ARP错误统计
        arp_errors = fetch_arp_errors()
        if arp_errors:
            output.append('\nARP错误统计:')
            for key, value in arp_errors.items():
                output.append(f"  {key}: {value}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取ARP表失败: {e}')
        return f'获取ARP表失败: {e}'
def fetch_arp_table(interface=None):
    """
    获取ARP表
    """
    entries = []

    try:
        # 构建命令
        cmd = ['ip', 'neigh', 'show']
        if interface:
            cmd.extend(['dev', interface])

        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    entry = analyze_arp_entry(line)
                    if entry:
                        entries.append(entry)

    except Exception as e:
        logger.error(f'获取ARP表失败: {e}')

    return entries
def analyze_arp_entry(line):
    """
    解析ARP条目
    """
    entry = {}

    try:
        parts = line.strip().split()
        if len(parts) < 4:
            return None

        # 解析IP地址
        entry['ip'] = parts[0]

        # 解析MAC地址
        if parts[2] == 'lladdr':
            entry['mac'] = parts[3]

        # 解析接口
        if 'dev' in parts:
            dev_index = parts.index('dev')
            if dev_index + 1 < len(parts):
                entry['interface'] = parts[dev_index + 1]

        # 解析状态
        states = ['REACHABLE', 'STALE', 'PERMANENT', 'NONE', 'FAILED', 'INCOMPLETE']
        for state in states:
            if state in parts:
                entry['state'] = state
                break

        # 解析类型（静态/动态）
        if 'PERMANENT' in parts:
            entry['type'] = 'static'
        else:
            entry['type'] = 'dynamic'

        # 估算过期时间
        if entry.get('state') == 'REACHABLE':
            entry['expires'] = '~120秒'
        elif entry.get('state') == 'STALE':
            entry['expires'] = '已过期'
        elif entry.get('type') == 'static':
            entry['expires'] = '永久'

    except Exception as e:
        logger.error(f'解析ARP条目失败: {e}')

    return entry
def display_arp_entry(output, entry):
    """
    显示ARP条目
    """
    output.append(f"  IP地址: {entry.get('ip', '未知')}")
    output.append(f"    MAC地址: {entry.get('mac', '未知')}")
    output.append(f"    接口: {entry.get('interface', '未知')}")
    output.append(f"    类型: {entry.get('type', '未知')}")
    output.append(f"    状态: {entry.get('state', '未知')}")
    output.append(f"    过期时间: {entry.get('expires', '未知')}")
def fetch_arp_stats(arp_entries):
    """
    获取ARP表统计信息
    """
    stats = {}

    if arp_entries:
        stats['总条目数'] = len(arp_entries)
        stats['静态条目数'] = len([entry for entry in arp_entries if entry.get('type') == 'static'])
        stats['动态条目数'] = len([entry for entry in arp_entries if entry.get('type') == 'dynamic'])

        # 按状态统计
        state_counts = {}
        for entry in arp_entries:
            state = entry.get('state', '未知')
            state_counts[state] = state_counts.get(state, 0) + 1
        stats['状态分布'] = ', '.join([f"{k}:{v}" for k, v in state_counts.items()])

        # 按接口统计
        interface_counts = {}
        for entry in arp_entries:
            interface = entry.get('interface', '未知')
            interface_counts[interface] = interface_counts.get(interface, 0) + 1
        stats['接口分布'] = ', '.join([f"{k}:{v}" for k, v in interface_counts.items()])

    return stats
