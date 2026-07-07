import logging
import os
import platform
import subprocess

from mcp_tools.cmd_safety_guard import validate_device_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(label)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_switch_bridge')

def fetch_hw_switch_bridge(switch_type=None):
    """
    采集物理桥接/交换机硬件信息

    参数:
        switch_type: 信息类型，可选值：
            - 'bridge': 物理桥接信息
            - 'onboard': 板载交换机信息
            - 'external': 外接交换机信息
            - 'state': 交换机状态
            - None: 获取所有信息

    返回:
        格式化的物理桥接/交换机硬件信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 物理桥接/交换机硬件信息 ===')

        # 获取物理桥接/交换机信息
        switch_info = fetch_switch_details()

        # 根据参数返回不同信息
        if switch_type == 'bridge':
            bridges = switch_info.get('bridges', [])
            if bridges:
                bridge_info = '\n'.join([f"  桥接 {i}: {bridge}" for i, bridge in enumerate(bridges)])
                return f"物理桥接信息:\n{bridge_info}"
            else:
                return "物理桥接信息: 未检测到桥接设备"
        elif switch_type == 'onboard':
            onboard_switches = switch_info.get('onboard_switches', [])
            if onboard_switches:
                onboard_info = '\n'.join([f"  板载交换机 {i}: {switch}" for i, switch in enumerate(onboard_switches)])
                return f"板载交换机信息:\n{onboard_info}"
            else:
                return "板载交换机信息: 未检测到板载交换机"
        elif switch_type == 'external':
            external_switches = switch_info.get('external_switches', [])
            if external_switches:
                external_info = '\n'.join([f"  外接交换机 {i}: {switch}" for i, switch in enumerate(external_switches)])
                return f"外接交换机信息:\n{external_info}"
            else:
                return "外接交换机信息: 未检测到外接交换机"
        elif switch_type == 'state':
            statuses = switch_info.get('statuses', [])
            if statuses:
                status_info = '\n'.join([f"  设备 {i}: {state}" for i, state in enumerate(statuses)])
                return f"交换机状态:\n{status_info}"
            else:
                return "交换机状态: 未检测到交换机设备"
        else:
            # 获取所有信息
            output.append(f"检测到桥接设备数量: {len(switch_info.get('bridges', []))}")
            output.append(f"检测到板载交换机数量: {len(switch_info.get('onboard_switches', []))}")
            output.append(f"检测到外接交换机数量: {len(switch_info.get('external_switches', []))}")

            # 物理桥接信息
            bridges = switch_info.get('bridges', [])
            if bridges:
                output.append("\n物理桥接详细信息:")
                for i, bridge in enumerate(bridges):
                    output.append(f"  桥接 {i}:")
                    output.append(f"    名称: {bridge.get('label', 'Unknown')}")
                    output.append(f"    状态: {bridge.get('state', 'Unknown')}")
                    output.append(f"    接口: {bridge.get('interfaces', 'Unknown')}")
                    output.append(f"    MAC地址: {bridge.get('mac', 'Unknown')}")
                    output.append(f"    类型: {bridge.get('type', 'Unknown')}")

            # 板载交换机信息
            onboard_switches = switch_info.get('onboard_switches', [])
            if onboard_switches:
                output.append("\n板载交换机详细信息:")
                for i, switch in enumerate(onboard_switches):
                    output.append(f"  板载交换机 {i}:")
                    output.append(f"    型号: {switch.get('model', 'Unknown')}")
                    output.append(f"    厂商: {switch.get('vendor', 'Unknown')}")
                    output.append(f"    端口数: {switch.get('ports', 'Unknown')}")
                    output.append(f"    状态: {switch.get('state', 'Unknown')}")
                    output.append(f"    标识: {switch.get('identifier', 'Unknown')}")

            # 外接交换机信息
            external_switches = switch_info.get('external_switches', [])
            if external_switches:
                output.append("\n外接交换机详细信息:")
                for i, switch in enumerate(external_switches):
                    output.append(f"  外接交换机 {i}:")
                    output.append(f"    型号: {switch.get('model', 'Unknown')}")
                    output.append(f"    厂商: {switch.get('vendor', 'Unknown')}")
                    output.append(f"    端口数: {switch.get('ports', 'Unknown')}")
                    output.append(f"    状态: {switch.get('state', 'Unknown')}")
                    output.append(f"    标识: {switch.get('identifier', 'Unknown')}")
                    output.append(f"    连接接口: {switch.get('interface', 'Unknown')}")

            # 网络拓扑信息
            try:
                topology_info = fetch_network_topology()
                if topology_info:
                    output.append("\n网络拓扑信息:")
                    for line in topology_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取网络拓扑信息失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取物理桥接/交换机硬件信息失败: {e}')
        return f'获取物理桥接/交换机硬件信息失败: {e}'
def fetch_switch_details():
    """
    获取物理桥接/交换机详细信息

    返回:
        物理桥接/交换机详细信息字典
    """
    try:
        switch_info = {
            'bridges': [],
            'onboard_switches': [],
            'external_switches': [],
            'statuses': []
        }

        if platform.system() == 'Linux':
            # 尝试获取网络桥接信息
            try:
                bridges = fetch_linux_bridges()
                for bridge in bridges:
                    switch_info['bridges'].append(bridge)
                    switch_info['statuses'].append(f"{bridge.get('label')}: {bridge.get('state')}")
            except Exception:
                pass

            # 尝试获取板载交换机信息
            try:
                onboard_switches = fetch_onboard_switches()
                for switch in onboard_switches:
                    switch_info['onboard_switches'].append(switch)
                    switch_info['statuses'].append(f"{switch.get('model')}: {switch.get('state')}")
            except Exception:
                pass

            # 尝试获取外接交换机信息
            try:
                external_switches = fetch_external_switches()
                for switch in external_switches:
                    switch_info['external_switches'].append(switch)
                    switch_info['statuses'].append(f"{switch.get('model')}: {switch.get('state')}")
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                bridges = fetch_macos_bridges()
                for bridge in bridges:
                    switch_info['bridges'].append(bridge)
                    switch_info['statuses'].append(f"{bridge.get('label')}: {bridge.get('state')}")
            except Exception:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                bridges = fetch_windows_bridges()
                for bridge in bridges:
                    switch_info['bridges'].append(bridge)
                    switch_info['statuses'].append(f"{bridge.get('label')}: {bridge.get('state')}")
            except Exception:
                pass

        return switch_info

    except Exception as e:
        logger.error(f'获取物理桥接/交换机详细信息失败: {e}')
        return {
            'bridges': [],
            'onboard_switches': [],
            'external_switches': [],
            'statuses': []
        }
