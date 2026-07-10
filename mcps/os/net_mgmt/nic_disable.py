import logging
import os
import subprocess
import time

from mcp_tools.cmd_safety_guard import validate_identifier_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_nic_down')

def fetch_net_nic_down():
    """
    采集禁用网卡（未启用的网卡/硬件状态/配置信息/禁用原因）

    返回:
        格式化的禁用网卡信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 禁用网卡 ===')

        # 获取所有网络接口
        all_interfaces = fetch_network_interfaces()
        if not all_interfaces:
            output.append('无法获取网络接口列表')
            output.append('=====================')
            return '\n'.join(output)

        # 识别禁用的网卡
        down_interfaces = [iface for iface in all_interfaces if is_interface_down(iface)]

        if not down_interfaces:
            output.append('没有发现禁用的网卡')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'发现 {len(down_interfaces)} 个禁用的网卡')

        # 采集每个禁用网卡的详细信息
        for iface in down_interfaces:
            down_info = fetch_down_interface_info(iface)
            if down_info:
                output.append(f"\n网卡 {iface}:")
                for key, value in down_info.items():
                    output.append(f"  {key}: {value}")

        # 采集可能的禁用原因分析
        disable_reasons = examine_disable_reasons(down_interfaces)
        if disable_reasons:
            output.append('\n禁用原因分析:')
            for reason in disable_reasons:
                output.append(f"  - {reason}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取禁用网卡失败: {e}')
        return f'获取禁用网卡失败: {e}'
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
def is_interface_down(interface):
    """
    检查接口是否禁用
    """
    # 安全校验：验证 interface 参数
    is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
    if not is_valid:
        logger.error(f'网络接口名称不合法：{error_msg}')
        return False

    try:
        # 检查 operstate
        operstate_path = f'/sys/class/net/{interface}/operstate'
        if os.path.exists(operstate_path):
            with open(operstate_path, 'r') as f:
                operstate = f.read().strip()
                return operstate != 'up'

        # 检查 carrier
        carrier_path = f'/sys/class/net/{interface}/carrier'
        if os.path.exists(carrier_path):
            with open(carrier_path, 'r') as f:
                carrier = f.read().strip()
                return carrier != '1'

    except Exception:
        pass

    return False
def fetch_down_interface_info(interface):
    """
    获取禁用网卡的详细信息
    """
    # 安全校验：验证 interface 参数
    is_valid, error_msg = validate_identifier_param(interface, allow_slash=False)
    if not is_valid:
        logger.error(f'网络接口名称不合法：{error_msg}')
        return {}

    details = {}

    try:
        # 获取操作状态
        operstate_path = f'/sys/class/net/{interface}/operstate'
        if os.path.exists(operstate_path):
            with open(operstate_path, 'r') as f:
                operstate = f.read().strip()
                details['操作状态'] = operstate

        # 获取链路状态
        carrier_path = f'/sys/class/net/{interface}/carrier'
        if os.path.exists(carrier_path):
            with open(carrier_path, 'r') as f:
                carrier = f.read().strip()
                details['链路状态'] = '连接' if carrier == '1' else '断开'

        # 获取MAC地址
        addr_path = f'/sys/class/net/{interface}/address'
        if os.path.exists(addr_path):
            with open(addr_path, 'r') as f:
                mac = f.read().strip()
                details['MAC地址'] = mac

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
                details['接口类型'] = type_map.get(type_val, f'未知类型 ({type_val})')

        # 获取MTU
        mtu_path = f'/sys/class/net/{interface}/mtu'
        if os.path.exists(mtu_path):
            with open(mtu_path, 'r') as f:
                mtu = f.read().strip()
                details['MTU'] = mtu

        # 检查是否有配置文件
        config_files = locate_interface_config_files(interface)
        if config_files:
            details['配置文件'] = ', '.join(config_files)
        else:
            details['配置文件'] = '无'

        # 尝试获取IP配置（如果有）
        try:
            output = subprocess.run(['ip', 'addr', 'show', interface], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if 'inet ' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            details['IP配置'] = parts[1]
                            break
        except Exception:
            pass

        details.setdefault('IP配置', '无')
        # 分析可能的禁用原因
        details['可能的禁用原因'] = examine_interface_disable_reason(interface)

    except Exception as e:
        logger.error(f'获取禁用网卡信息失败: {e}')

    return details
