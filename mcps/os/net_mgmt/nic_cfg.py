import logging
import os
import subprocess
import time

from mcp_tools.cmd_safety_guard import validate_identifier_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_nic_config')

def fetch_net_nic_config(interface=None):
    """
    采集网卡静态配置（所有网卡 IP/子网掩码/网关/广播地址/MTU/是否启用）

    参数:
        interface: 网络接口名称，如 "eth0"

    返回:
        格式化的网卡静态配置信息字符串
    """
    try:
        # 安全校验：验证接口名称参数
        if interface is not None:
            is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
            if not is_valid:
                logger.error(f'网络接口名称不合法：{error_msg}')
                return f'获取网卡静态配置失败：网络接口名称不合法：{error_msg}'

        # 基本信息
        output = []
        output.append('=== 网卡静态配置 ===')

        # 获取网络接口列表
        interfaces = []
        if interface:
            # 检查接口是否存在
            if os.path.exists(f'/sys/class/net/{interface}'):
                interfaces.append(interface)
            else:
                output.append(f'错误: 接口 {interface} 不存在')
                output.append('=====================')
                return '\n'.join(output)
        else:
            # 获取所有网络接口
            interfaces = fetch_network_interfaces()

        if not interfaces:
            output.append('无法获取网络接口列表')
            output.append('=====================')
            return '\n'.join(output)

        # 采集每个接口的配置
        for iface in interfaces:
            nic_config = fetch_interface_config(iface)
            if nic_config:
                output.append(f"\n接口 {iface}:")
                for key, value in nic_config.items():
                    output.append(f"  {key}: {value}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取网卡静态配置失败: {e}')
        return f'获取网卡静态配置失败: {e}'
def fetch_network_interfaces():
    """
    获取网络接口列表
    """
    interfaces = []

    try:
        # 读取/sys/class/net目录
        net_dir = '/sys/class/net'
        if os.path.exists(net_dir):
            for item in os.listdir(net_dir):
                interfaces.append(item)

    except Exception as e:
        logger.error(f'获取网络接口列表失败: {e}')

    return interfaces
def fetch_interface_config(interface):
    """
    获取单个接口的配置
    """
    settings = {}

    try:
        # 检查接口是否启用
        operstate_path = f'/sys/class/net/{interface}/operstate'
        if os.path.exists(operstate_path):
            with open(operstate_path, 'r') as f:
                operstate = f.read().strip()
                settings['是否启用'] = '是' if operstate == 'up' else '否'
        else:
            settings['是否启用'] = '未知'

        # 获取MTU
        mtu_path = f'/sys/class/net/{interface}/mtu'
        if os.path.exists(mtu_path):
            with open(mtu_path, 'r') as f:
                mtu = f.read().strip()
                settings['MTU'] = mtu

        # 获取IP地址和子网掩码
        try:
            output = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if 'inet ' in line:
                        # 提取IPv4地址
                        parts = line.split()
                        if len(parts) >= 2:
                            ip_netmask = parts[1]
                            settings['IP地址/子网掩码'] = ip_netmask
                    elif 'inet6 ' in line:
                        # 提取IPv6地址
                        parts = line.split()
                        if len(parts) >= 2:
                            ipv6_addr = parts[1]
                            settings.setdefault('IPv6地址', [])
                            settings['IPv6地址'].append(ipv6_addr)
        except Exception as e:
            logger.error(f'获取IP地址失败: {e}')

        # 获取广播地址
        try:
            output = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if 'brd ' in line:
                        parts = line.split('brd ')
                        if len(parts) >= 2:
                            broadcast = parts[1].split()[0]
                            settings['广播地址'] = broadcast
        except Exception as e:
            logger.error(f'获取广播地址失败: {e}')

        # 获取网关
        try:
            output = subprocess.run(['ip', 'route', 'show', 'dev', interface], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            gateway = parts[2]
                            settings['网关'] = gateway
        except Exception as e:
            logger.error(f'获取网关失败: {e}')

        # 获取接口类型
        if os.path.exists(f'/sys/class/net/{interface}/type'):
            with open(f'/sys/class/net/{interface}/type', 'r') as f:
                type_val = f.read().strip()
                type_map = {
                    '1': '以太网',
                    '24': 'IEEE 802.11无线',
                    '512': 'PPP',
                    '768': 'IPIP隧道',
                    '769': 'GRE隧道',
                    '772': 'VLAN',
                    '776': 'LOOPBACK',
                    '778': '桥接',
                    '783': 'bond',
                    '784': 'TUN',
                    '785': 'TAP'
                }
                settings['接口类型'] = type_map.get(type_val, f'未知类型 ({type_val})')

        # 获取MAC地址
        addr_path = f'/sys/class/net/{interface}/address'
        if os.path.exists(addr_path):
            with open(addr_path, 'r') as f:
                mac = f.read().strip()
                settings['MAC地址'] = mac

        # 获取接口状态
        carrier_path = f'/sys/class/net/{interface}/carrier'
        if os.path.exists(carrier_path):
            with open(carrier_path, 'r') as f:
                carrier = f.read().strip()
                settings['链路状态'] = '连接' if carrier == '1' else '断开'

    except Exception as e:
        logger.error(f'获取接口配置失败: {e}')

    return settings

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_net_nic_config",
    "function": fetch_net_nic_config,
    "description": "采集网卡静态配置（所有网卡IP/子网掩码/网关/广播地址/MTU/是否启用）",
    "parameters": {
        "type": "object",
        "properties": {
            "interface": {
                "type": "string",
                "description": "网络接口名称，如 \"eth0\""
            }
        },
        "required": []
    }
}
