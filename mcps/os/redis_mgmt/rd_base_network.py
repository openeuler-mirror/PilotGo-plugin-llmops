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
def fetch_interface_info(pid):
    """
    获取绑定网卡信息
    """
    interface_info = {}

    try:
        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'bind'],
            capture_output=True,
            text=True,
            deadline=5
        )

        bind_addresses = []
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'bind' and i + 1 < len(lines):
                    bind_address = lines[i + 1].strip()
                    bind_addresses = bind_address.split()
                    break

        if bind_addresses:
            interface_info['绑定IP地址'] = ', '.join(bind_addresses)

        output = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)

        if output.returncode == 0:
            interfaces = {}
            current_interface = None

            for line in output.stdout.split('\n'):
                if line.strip().startswith('inet'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip_address = parts[1].split('/')[0]
                        if current_interface:
                            if current_interface not in interfaces:
                                interfaces[current_interface] = []
                            interfaces[current_interface].append(ip_address)
                elif ':' in line and not line.strip().startswith(' '):
                    current_interface = line.split(':')[1].strip()

            if bind_addresses:
                bound_interfaces = []
                for bind_addr in bind_addresses:
                    if bind_addr == '*':
                        bound_interfaces = list(interfaces.keys())
                        break
                    elif bind_addr == '0.0.0.0':
                        bound_interfaces = list(interfaces.keys())
                        break
                    else:
                        for interface, ips in interfaces.items():
                            if bind_addr in ips:
                                bound_interfaces.append(interface)

                if bound_interfaces:
                    interface_info['绑定网卡'] = ', '.join(sorted(set(bound_interfaces)))

        output = subprocess.run(['ifconfig'], capture_output=True, text=True)

        if output.returncode == 0:
            interfaces = []
            for line in output.stdout.split('\n'):
                if ':' in line and 'flags=' in line:
                    interface_name = line.split(':')[0].strip()
                    interfaces.append(interface_name)

            if interfaces:
                interface_info['可用网卡'] = ', '.join(interfaces)

        output = subprocess.run(
            ['ip', 'route', 'get', '1.1.1.1'],  # NOSONAR
            capture_output=True,
            text=True
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for line in lines:
                if 'dev' in line:
                    parts = line.split()
                    if 'dev' in parts:
                        dev_index = parts.index('dev')
                        if dev_index + 1 < len(parts):
                            interface_info['默认网卡'] = parts[dev_index + 1]
                    break

        output = subprocess.run(['hostname', '-I'], capture_output=True, text=True)

        if output.returncode == 0:
            interface_info['主机IP地址'] = output.stdout.strip()

        output = subprocess.run(
            ['ip', 'addr', 'show', '|', 'grep', 'inet'],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0:
            inet_lines = output.stdout.strip().split('\n')
            interface_info['所有IP地址'] = ', '.join([line.split()[1].split('/')[0] for line in inet_lines if line.strip()])

    except Exception as e:
        logger.error(f'获取绑定网卡信息失败: {e}')

    return interface_info
def fetch_firewall_info(pid):
    """
    获取防火墙规则
    """
    firewall_info = {}

    try:
        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'port'],
            capture_output=True,
            text=True,
            deadline=5
        )

        redis_port = None
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'port' and i + 1 < len(lines):
                    redis_port = lines[i + 1].strip()
                    break

        output = subprocess.run(['systemctl', 'is-active', 'firewalld'], capture_output=True, text=True)

        if output.returncode == 0:
            firewall_info['Firewalld状态'] = output.stdout.strip()

        output = subprocess.run(['systemctl', 'is-active', 'ufw'], capture_output=True, text=True)

        if output.returncode == 0:
            firewall_info['UFW状态'] = output.stdout.strip()

        output = subprocess.run(['systemctl', 'is-active', 'iptables'], capture_output=True, text=True)

        if output.returncode == 0:
            firewall_info['Iptables状态'] = output.stdout.strip()

        output = subprocess.run(['iptables', '-L', '-n', '2>/dev/null'], capture_output=True, text=True)

        if output.returncode == 0:
            if redis_port:
                redis_rules = [line.strip() for line in output.stdout.split('\n') if redis_port in line or 'dpt:' + redis_port in line]

                if redis_rules:
                    firewall_info['Iptables Redis规则'] = '\n    '.join(redis_rules)
                else:
                    firewall_info['Iptables Redis规则'] = '未找到Redis端口规则'
            else:
                firewall_info['Iptables规则数量'] = str(len([line for line in output.stdout.split('\n') if line.strip()]))

        output = subprocess.run(['firewall-cmd', '--list-ports', '2>/dev/null'], capture_output=True, text=True)

        if output.returncode == 0:
            ports = output.stdout.strip()
            if redis_port and redis_port in ports:
                firewall_info['Firewalld开放端口'] = ports
                firewall_info['Redis端口状态'] = '已开放'
            else:
                firewall_info['Firewalld开放端口'] = ports
                if redis_port:
                    firewall_info['Redis端口状态'] = '未开放'

        output = subprocess.run(['ufw', 'status', '2>/dev/null'], capture_output=True, text=True)

        if output.returncode == 0:
            ufw_status = output.stdout.strip()
            firewall_info['UFW状态详情'] = ufw_status

            if redis_port and redis_port in ufw_status:
                firewall_info['Redis端口UFW状态'] = '已开放'
            elif redis_port:
                firewall_info['Redis端口UFW状态'] = '未开放'

        output = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)

        if output.returncode == 0:
            if redis_port:
                port_listening = False
                for line in output.stdout.split('\n'):
                    if f':{redis_port}' in line and 'LISTEN' in line:
                        port_listening = True
                        break

                firewall_info['端口监听状态'] = '正在监听' if port_listening else '未监听'

        output = subprocess.run(['nc', '-zv', '127.0.0.1', str(redis_port), '2>&1'], capture_output=True, text=True)

        if output.returncode == 0:
            firewall_info['本地端口连通性'] = '可连接'
        else:
            firewall_info['本地端口连通性'] = '不可连接'

    except Exception as e:
        logger.error(f'获取防火墙规则失败: {e}')

    return firewall_info
def fetch_whitelist_info(pid):
    """
    获取白名单配置
    """
    whitelist_info = {}

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
                    whitelist_info['绑定地址(白名单)'] = bind_address

                    if bind_address == '*':
                        whitelist_info['访问限制'] = '无限制（所有地址）'
                    elif bind_address == '127.0.0.1':
                        whitelist_info['访问限制'] = '仅本地访问'
                    else:
                        whitelist_info['访问限制'] = f'仅指定地址: {bind_address}'
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
                    whitelist_info['保护模式'] = '启用' if protected_mode == 'yes' else '禁用'

                    if protected_mode == 'yes':
                        whitelist_info['保护模式说明'] = '启用保护模式时，Redis只接受来自本地回环地址的连接'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'requirepass'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'requirepass' and i + 1 < len(lines):
                    password = lines[i + 1].strip()  # NOSONAR
                    if password:  # NOSONAR
                        whitelist_info['密码认证'] = '已设置'
                    else:
                        whitelist_info['密码认证'] = '未设置'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'rename-command'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            renamed_commands = [lines[i + 1].strip() for i in range(0, len(lines) - 1) if lines[i].strip() == 'rename-command' and i + 1 < len(lines)]

            if renamed_commands:
                whitelist_info['重命名命令'] = ', '.join(renamed_commands)

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'rename-command CONFIG'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'rename-command' and i + 1 < len(lines):
                    renamed_config = lines[i + 1].strip()
                    if renamed_config and renamed_config != '':
                        whitelist_info['CONFIG命令'] = f'已重命名为: {renamed_config}'
                    else:
                        whitelist_info['CONFIG命令'] = '未重命名（安全风险）'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'rename-command FLUSHALL'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'rename-command' and i + 1 < len(lines):
                    renamed_flushall = lines[i + 1].strip()
                    if renamed_flushall and renamed_flushall != '':
                        whitelist_info['FLUSHALL命令'] = f'已重命名为: {renamed_flushall}'
                    else:
                        whitelist_info['FLUSHALL命令'] = '未重命名（安全风险）'
                    break

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'rename-command FLUSHDB'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'rename-command' and i + 1 < len(lines):
                    renamed_flushdb = lines[i + 1].strip()
                    if renamed_flushdb and renamed_flushdb != '':
                        whitelist_info['FLUSHDB命令'] = f'已重命名为: {renamed_flushdb}'
                    else:
                        whitelist_info['FLUSHDB命令'] = '未重命名（安全风险）'
                    break

    except Exception as e:
        logger.error(f'获取白名单配置失败: {e}')

    return whitelist_info
def fetch_connections_info(pid):
    """
    获取连接信息
    """
    connections_info = {}

    try:
        output = subprocess.run(
            ['redis-cli', 'INFO', 'clients'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('connected_clients:'):
                    connections_info['已连接客户端数'] = line.split(':')[1]
                elif line.startswith('blocked_clients:'):
                    connections_info['阻塞客户端数'] = line.split(':')[1]
                elif line.startswith('tracking_clients:'):
                    connections_info['跟踪客户端数'] = line.split(':')[1]
                elif line.startswith('clients_in_timeout_table:'):
                    connections_info['超时表客户端数'] = line.split(':')[1]

        output = subprocess.run(
            ['redis-cli', 'CLIENT', 'LIST'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            client_lines = output.stdout.strip().split('\n')
            connections_info['客户端列表数量'] = str(len(client_lines))

            if client_lines:
                connections_info['客户端详情'] = '前5个客户端:'
                for i, client_line in enumerate(client_lines[:5], 1):
                    connections_info[f'客户端{i}'] = client_line

        output = subprocess.run(
            ['ss', '-tnp', '|', 'grep', str(pid)],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            lines = output.stdout.strip().split('\n')
            connections_info['TCP连接数'] = str(len(lines))

            established_count = 0
            listen_count = 0
            for line in lines:
                if 'ESTAB' in line:
                    established_count += 1
                elif 'LISTEN' in line:
                    listen_count += 1

            connections_info['已建立连接'] = str(established_count)
            connections_info['监听连接'] = str(listen_count)

        output = subprocess.run(
            ['netstat', '-tnp', '2>/dev/null', '|', 'grep', str(pid)],
            capture_output=True,
            text=True,
            shell=True
        )

        if output.returncode == 0 and output.stdout.strip():
            lines = output.stdout.strip().split('\n')
            connections_info['Netstat连接数'] = str(len(lines))

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'maxclients'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'maxclients' and i + 1 < len(lines):
                    maxclients = lines[i + 1].strip()
                    connections_info['最大客户端数'] = maxclients
                    break

        output = subprocess.run(
            ['redis-cli', 'INFO', 'stats'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            info_lines = output.stdout.split('\n')
            for line in info_lines:
                if line.startswith('total_connections_received:'):
                    connections_info['总连接接收数'] = line.split(':')[1]
                elif line.startswith('rejected_connections:'):
                    connections_info['拒绝连接数'] = line.split(':')[1]
                elif line.startswith('total_net_input_bytes:'):
                    connections_info['网络输入字节'] = line.split(':')[1]
                elif line.startswith('total_net_output_bytes:'):
                    connections_info['网络输出字节'] = line.split(':')[1]

        output = subprocess.run(
            ['redis-cli', 'CONFIG', 'GET', 'deadline'],
            capture_output=True,
            text=True,
            deadline=5
        )

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'deadline' and i + 1 < len(lines):
                    deadline = lines[i + 1].strip()
                    if deadline == '0':
                        connections_info['连接超时'] = '永不超时'
                    else:
                        connections_info['连接超时'] = f"{deadline} 秒"
                    break

    except Exception as e:
        logger.error(f'获取连接信息失败: {e}')

    return connections_info

TOOL_CONFIG = {
    "name": "fetch_redis_base_network",
    "function": fetch_redis_base_network,
    "description": "采集Redis监听IP/端口（TCP/UDP）、绑定网卡、防火墙放行规则、连接白名单配置",
    "parameters": {
        "type": "object",
        "properties": {
            "network_type": {
                "type": "string",
                "description": "指定要采集的网络信息类型，可选值：listen（监听信息）、interface（绑定网卡信息）、firewall（防火墙规则）、whitelist（白名单配置）、connections（连接信息）、all（所有网络信息）",
                "enum": ["listen", "interface", "firewall", "whitelist", "connections", "all"]
            }
        },
        "required": []
    }
}
