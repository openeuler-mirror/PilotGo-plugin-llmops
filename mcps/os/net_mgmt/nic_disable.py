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
