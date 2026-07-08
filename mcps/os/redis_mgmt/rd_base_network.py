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
def fetch_network_info_from_config():
    """
    从配置文件获取网络信息
    """
    network_info = {}

    try:
        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'bind'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'bind' and i + 1 < len(lines):
                    bind_address = lines[i + 1].strip()
                    network_info['绑定地址'] = bind_address
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'port'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'port' and i + 1 < len(lines):
                    port = lines[i + 1].strip()
                    network_info['监听端口'] = port
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'protected-mode'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'protected-mode' and i + 1 < len(lines):
                    protected_mode = lines[i + 1].strip()
                    network_info['保护模式'] = '启用' if protected_mode == 'yes' else '禁用'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'tcp-backlog'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'tcp-backlog' and i + 1 < len(lines):
                    backlog = lines[i + 1].strip()
                    network_info['TCP连接队列'] = backlog
                    break

    except Exception as e:
        logger.error(f'从配置文件获取网络信息失败: {e}')

    return network_info
def fetch_listen_info(pid):
    """
    获取监听信息
    """
    listen_info = {}

    try:
        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'bind'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'bind' and i + 1 < len(lines):
                    bind_address = lines[i + 1].strip()
                    listen_info['绑定地址'] = bind_address
                    if bind_address == '*':
                        listen_info['监听地址'] = '所有地址 (0.0.0.0)'
                    elif bind_address == '127.0.0.1':
                        listen_info['监听地址'] = '本地回环 (127.0.0.1)'
                    else:
                        listen_info['监听地址'] = bind_address
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'port'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'port' and i + 1 < len(lines):
                    port = lines[i + 1].strip()
                    listen_info['监听端口'] = port
                    listen_info['监听协议'] = 'TCP'
                    break

        output = subprocess.run(
            ['redis-cli', 'INFO', 'server'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('tcp_port:'):
                    listen_info['TCP端口'] = line.split(':')[1]
                elif line.startswith('os:'):
                    listen_info['操作系统'] = line.split(':')[1]

        output = subprocess.run(
            ['ss', '-tlnp', '|', 'grep', str(pid)],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            lines = output.stdout.strip().split('\n')
            listen_info['监听套接字数量'] = str(len(lines))
            for i, line in enumerate(lines, 1):
                parts = line.split()
                if len(parts) >= 5:
                    listen_info[f'监听{i}'] = f"协议: {parts[0]}, 状态: {parts[1]}, 本地地址: {parts[4]}"

        output = subprocess.run(
            ['netstat', '-tlnp', '2>/dev/null', '|', 'grep', str(pid)],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            lines = output.stdout.strip().split('\n')
            for i, line in enumerate(lines, 1):
                if 'redis' in line.lower():
                    parts = line.split()
                    if len(parts) >= 4:
                        local_address = parts[3]
                        listen_info[f'Netstat监听{i}'] = f"本地地址: {local_address}"

        output = subprocess.run(['lsof', '-p', str(pid), '-i', '-P'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for line in lines:
                if 'LISTEN' in line and 'redis' in line.lower():
                    parts = line.split()
                    if len(parts) >= 9:
                        protocol = parts[4]
                        local_address = parts[8]
                        listen_info['LSOF监听'] = f"协议: {protocol}, 本地地址: {local_address}"
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'protected-mode'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'protected-mode' and i + 1 < len(lines):
                    protected_mode = lines[i + 1].strip()
                    listen_info['保护模式'] = '启用' if protected_mode == 'yes' else '禁用'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'tcp-backlog'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'tcp-backlog' and i + 1 < len(lines):
                    backlog = lines[i + 1].strip()
                    listen_info['TCP连接队列'] = backlog
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'tcp-keepalive'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'tcp-keepalive' and i + 1 < len(lines):
                    keepalive = lines[i + 1].strip()
                    listen_info['TCP保活时间'] = f"{keepalive} 秒"
                    break

    except Exception as e:
        logger.error(f'获取监听信息失败: {e}')

    return listen_info
