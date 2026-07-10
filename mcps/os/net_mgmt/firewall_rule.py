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
logger = logging.getLogger('net_firewall_rule')

def fetch_net_firewall_rule():
    """
    采集防火墙规则（iptables/ufw/firewalld的规则/链/动作/端口/IP限制）

    返回:
        格式化的防火墙规则信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 防火墙规则 ===')

        # 采集iptables规则
        iptables_rules = fetch_iptables_rules()
        if iptables_rules:
            output.append('\niptables规则:')
            for rule in iptables_rules:
                output.append(f"  - {rule}")

        # 采集ufw规则
        ufw_rules = fetch_ufw_rules()
        if ufw_rules:
            output.append('\nufw规则:')
            for rule in ufw_rules:
                output.append(f"  - {rule}")

        # 采集firewalld规则
        firewalld_rules = fetch_firewalld_rules()
        if firewalld_rules:
            output.append('\nfirewalld规则:')
            for rule in firewalld_rules:
                output.append(f"  - {rule}")

        # 采集防火墙状态
        firewall_status = fetch_firewall_status()
        if firewall_status:
            output.append('\n防火墙状态:')
            for key, value in firewall_status.items():
                output.append(f"  {key}: {value}")

        # 分析防火墙规则
        firewall_analysis = examine_firewall_rules(iptables_rules, ufw_rules, firewalld_rules)
        if firewall_analysis:
            output.append('\n防火墙规则分析:')
            for analysis in firewall_analysis:
                output.append(f"  - {analysis}")

        # 检查防火墙安全性
        firewall_security = verify_firewall_security(iptables_rules, ufw_rules, firewalld_rules)
        if firewall_security:
            output.append('\n防火墙安全性检查:')
            for check in firewall_security:
                output.append(f"  - {check}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取防火墙规则失败: {e}')
        return f'获取防火墙规则失败: {e}'
def fetch_iptables_rules():
    """
    获取iptables规则
    """
    rules = []

    try:
        # 检查iptables是否可用
        output = subprocess.run(['which', 'iptables'], capture_output=True, text=True)

        if output.returncode == 0:
            # 获取filter表规则
            filter_result = subprocess.run(['iptables', '-L', '-n', '--line-numbers'], capture_output=True, text=True)

            if filter_result.returncode == 0:
                lines = filter_result.stdout.strip().split('\n')
                chain = ''
                for line in lines:
                    if line.startswith('Chain'):
                        chain = line.strip()
                        rules.append(f"{chain}")
                    elif line and not line.startswith('target') and not line.startswith('---'):
                        rules.append(f"  {line.strip()}")

            # 获取nat表规则
            nat_result = subprocess.run(['iptables', '-t', 'nat', '-L', '-n', '--line-numbers'], capture_output=True, text=True)

            if nat_result.returncode == 0:
                lines = nat_result.stdout.strip().split('\n')
                if lines:
                    rules.append("\nnat表:")
                    for line in lines:
                        if line:
                            rules.append(f"  {line.strip()}")

    except Exception as e:
        logger.error(f'获取iptables规则失败: {e}')

    return rules
def fetch_ufw_rules():
    """
    获取ufw规则
    """
    rules = []

    try:
        # 检查ufw是否可用
        output = subprocess.run(['which', 'ufw'], capture_output=True, text=True)

        if output.returncode == 0:
            # 获取ufw状态
            status_result = subprocess.run(['ufw', 'state', 'verbose'], capture_output=True, text=True)

            if status_result.returncode == 0:
                lines = status_result.stdout.strip().split('\n')
                for line in lines:
                    if line:
                        rules.append(f"{line.strip()}")

    except Exception as e:
        logger.error(f'获取ufw规则失败: {e}')

    return rules
def fetch_firewalld_rules():
    """
    获取firewalld规则
    """
    rules = []

    try:
        # 检查firewalld是否可用
        output = subprocess.run(['which', 'firewall-cmd'], capture_output=True, text=True)

        if output.returncode == 0:
            # 获取firewalld状态
            status_result = subprocess.run(['firewall-cmd', '--state'], capture_output=True, text=True)

            if status_result.returncode == 0 and status_result.stdout.strip() == 'running':
                # 获取默认区域
                zone_result = subprocess.run(['firewall-cmd', '--get-default-zone'], capture_output=True, text=True)

                if zone_result.returncode == 0:
                    default_zone = zone_result.stdout.strip()
                    rules.append(f"默认区域: {default_zone}")

                # 获取活动区域
                active_zones_result = subprocess.run(['firewall-cmd', '--get-active-zones'], capture_output=True, text=True)

                if active_zones_result.returncode == 0:
                    active_zones = active_zones_result.stdout.strip().split('\n')
                    rules.append("活动区域:")
                    for zone in active_zones:
                        if zone:
                            rules.append(f"  {zone}")

                # 获取服务
                services_result = subprocess.run(['firewall-cmd', '--list-services'], capture_output=True, text=True)

                if services_result.returncode == 0:
                    services = services_result.stdout.strip()
                    if services:
                        rules.append(f"允许的服务: {services}")

                # 获取端口
                ports_result = subprocess.run(['firewall-cmd', '--list-ports'], capture_output=True, text=True)

                if ports_result.returncode == 0:
                    ports = ports_result.stdout.strip()
                    if ports:
                        rules.append(f"允许的端口: {ports}")

    except Exception as e:
        logger.error(f'获取firewalld规则失败: {e}')

    return rules
def fetch_firewall_status():
    """
    获取防火墙状态
    """
    state = {}

    try:
        # 检查iptables状态
        iptables_result = subprocess.run(['which', 'iptables'], capture_output=True, text=True)
        if iptables_result.returncode == 0:
            state['iptables'] = '已安装'
        else:
            state['iptables'] = '未安装'

        # 检查ufw状态
        ufw_result = subprocess.run(['which', 'ufw'], capture_output=True, text=True)
        if ufw_result.returncode == 0:
            ufw_status_result = subprocess.run(['ufw', 'state'], capture_output=True, text=True)
            state['ufw'] = ufw_status_result.stdout.strip()
        else:
            state['ufw'] = '未安装'

        # 检查firewalld状态
        firewalld_result = subprocess.run(['which', 'firewall-cmd'], capture_output=True, text=True)
        if firewalld_result.returncode == 0:
            firewalld_status_result = subprocess.run(['firewall-cmd', '--state'], capture_output=True, text=True)
            state['firewalld'] = firewalld_status_result.stdout.strip()
        else:
            state['firewalld'] = '未安装'

    except Exception as e:
        logger.error(f'获取防火墙状态失败: {e}')

    return state
def examine_firewall_rules(iptables_rules, ufw_rules, firewalld_rules):
    """
    分析防火墙规则
    """
    analysis = []

    try:
        # 统计规则数量
        total_rules = len(iptables_rules) + len(ufw_rules) + len(firewalld_rules)
        analysis.append(f"总规则数: {total_rules}")

        # 检查是否有开放的SSH端口
        ssh_open = False
        for rule in iptables_rules + ufw_rules + firewalld_rules:
            if '22' in rule and ('ACCEPT' in rule or 'ALLOW' in rule):
                ssh_open = True
                break
        if ssh_open:
            analysis.append('SSH端口已开放')
        else:
            analysis.append('SSH端口未开放')

        # 检查是否有开放的HTTP/HTTPS端口
        web_open = False
        for rule in iptables_rules + ufw_rules + firewalld_rules:
            if ('80' in rule or '443' in rule) and ('ACCEPT' in rule or 'ALLOW' in rule):
                web_open = True
                break
        if web_open:
            analysis.append('HTTP/HTTPS端口已开放')
        else:
            analysis.append('HTTP/HTTPS端口未开放')

    except Exception as e:
        logger.error(f'分析防火墙规则失败: {e}')

    return analysis
