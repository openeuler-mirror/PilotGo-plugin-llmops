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
