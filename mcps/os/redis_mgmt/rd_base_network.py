from datetime import datetime
import logging
import os
import re
import socket
import subprocess

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('redis_base_network')

def fetch_redis_base_network(network_type=None):
    """
    采集Redis监听IP/端口（TCP/UDP）、绑定网卡、防火墙放行规则、连接白名单配置

    参数:
        network_type: 指定要采集的网络信息类型，可选值：
                      - "listen": 仅采集监听信息（IP/端口）
                      - "interface": 仅采集绑定网卡信息
                      - "firewall": 仅采集防火墙规则
                      - "whitelist": 仅采集白名单配置
                      - "connections": 仅采集连接信息
                      - "all": 采集所有网络信息（默认）

    返回:
        格式化的Redis网络信息字符串
    """
    try:
        output = []
        output.append('=== Redis网络信息 ===')

        redis_pid = find_redis_pid()

        if not redis_pid:
            output.append('未检测到运行中的Redis进程')
            output.append('尝试通过配置文件和网络扫描获取网络信息...')

            network_info = fetch_network_info_from_config()
            if network_info:
                output.append('\n配置文件网络信息:')
                for key, value in network_info.items():
                    output.append(f"  {key}: {value}")

            output.append('=====================')
            return '\n'.join(output)

        output.append(f'检测到Redis进程: PID {redis_pid}')

        if network_type is None or network_type == "all" or network_type == "listen":
            listen_info = fetch_listen_info(redis_pid)
            if listen_info:
                output.append('\n监听信息:')
                for key, value in listen_info.items():
                    output.append(f"  {key}: {value}")

        if network_type is None or network_type == "all" or network_type == "interface":
            interface_info = fetch_interface_info(redis_pid)
            if interface_info:
                output.append('\n绑定网卡信息:')
                for key, value in interface_info.items():
                    output.append(f"  {key}: {value}")

        if network_type is None or network_type == "all" or network_type == "firewall":
            firewall_info = fetch_firewall_info(redis_pid)
            if firewall_info:
                output.append('\n防火墙规则:')
                for key, value in firewall_info.items():
                    output.append(f"  {key}: {value}")

        if network_type is None or network_type == "all" or network_type == "whitelist":
            whitelist_info = fetch_whitelist_info(redis_pid)
            if whitelist_info:
                output.append('\n白名单配置:')
                for key, value in whitelist_info.items():
                    output.append(f"  {key}: {value}")

        if network_type is None or network_type == "all" or network_type == "connections":
            connections_info = fetch_connections_info(redis_pid)
            if connections_info:
                output.append('\n连接信息:')
                for key, value in connections_info.items():
                    output.append(f"  {key}: {value}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis网络信息失败: {e}')
        return f'获取Redis网络信息失败: {e}'
