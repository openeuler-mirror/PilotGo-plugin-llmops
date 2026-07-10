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
