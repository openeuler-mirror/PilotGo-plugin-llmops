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
def fetch_linux_bridges():
    """
    获取Linux系统中的网络桥接信息

    返回:
        网络桥接信息列表
    """
    try:
        bridges = []

        # 尝试使用brctl命令
        try:
            output = subprocess.run(['brctl', 'show'], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.split('\n')[1:]
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            bridge_name = parts[0]

                            # 安全校验：验证桥接设备名
                            is_valid, error_msg = validate_device_name(bridge_name)
                            if not is_valid:
                                logger.warning(f'跳过不合法的桥接设备名 {bridge_name}: {error_msg}')
                                continue

                            interfaces = parts[3:] if len(parts) > 3 else []

                            # 获取桥接状态
                            state = 'Unknown'
                            try:
                                with open(f'/sys/class/net/{bridge_name}/operstate', 'r') as f:
                                    state = f.read().strip()
                            except Exception:
                                pass

                            # 获取桥接MAC地址
                            mac = 'Unknown'
                            try:
                                with open(f'/sys/class/net/{bridge_name}/address', 'r') as f:
                                    mac = f.read().strip()
                            except Exception:
                                pass

                            bridge = {
                                'label': bridge_name,
                                'state': state,
                                'interfaces': ', '.join(interfaces) if interfaces else 'None',
                                'mac': mac,
                                'type': 'Network Bridge',
                                'ports': len(interfaces)
                            }
                            bridges.append(bridge)
        except subprocess.SubprocessError:
            pass

        # 尝试使用ip命令
        try:
            output = subprocess.run(['ip', 'link', 'show', 'type', 'bridge'], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.split('\n')
                current_bridge = None

                for line in lines:
                    if line.strip() and not line.startswith(' '):
                        if current_bridge:
                            bridges.append(current_bridge)

                        parts = line.split(':')
                        if len(parts) >= 2:
                            bridge_name = parts[1].strip()
                            current_bridge = {
                                'label': bridge_name,
                                'state': 'Unknown',
                                'interfaces': 'Unknown',
                                'mac': 'Unknown',
                                'type': 'Network Bridge',
                                'ports': 'Unknown'
                            }
                    elif current_bridge and 'state' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            current_bridge['state'] = parts[1]
                    elif current_bridge and 'link/ether' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            current_bridge['mac'] = parts[1]

                if current_bridge:
                    bridges.append(current_bridge)
        except subprocess.SubprocessError:
            pass

        # 尝试从/sys获取桥接信息
        try:
            net_devices = os.listdir('/sys/class/net')
            for dev in net_devices:
                if dev != 'lo':
                    try:
                        if os.path.exists(f'/sys/class/net/{dev}/bridge'):
                            # 这是一个桥接设备
                            bridge_name = dev

                            # 检查是否已经存在
                            existing = False
                            for bridge in bridges:
                                if bridge.get('label') == bridge_name:
                                    existing = True
                                    break
                            if existing:
                                continue

                            # 获取状态
                            state = 'Unknown'
                            try:
                                with open(f'/sys/class/net/{bridge_name}/operstate', 'r') as f:
                                    state = f.read().strip()
                            except Exception:
                                pass

                            # 获取MAC地址
                            mac = 'Unknown'
                            try:
                                with open(f'/sys/class/net/{bridge_name}/address', 'r') as f:
                                    mac = f.read().strip()
                            except Exception:
                                pass

                            # 获取接口列表
                            interfaces = []
                            try:
                                if os.path.exists(f'/sys/class/net/{bridge_name}/brif'):
                                    interfaces = os.listdir(f'/sys/class/net/{bridge_name}/brif')
                            except Exception:
                                pass

                            bridge = {
                                'label': bridge_name,
                                'state': state,
                                'interfaces': ', '.join(interfaces) if interfaces else 'None',
                                'mac': mac,
                                'type': 'Network Bridge',
                                'ports': len(interfaces)
                            }
                            bridges.append(bridge)
                    except Exception:
                        pass
        except Exception:
            pass

        return bridges

    except Exception as e:
        logger.error(f'获取Linux网络桥接信息失败: {e}')
        return []
def fetch_onboard_switches():
    """
    获取板载交换机信息

    返回:
        板载交换机信息列表
    """
    try:
        onboard_switches = []

        # 尝试使用lspci命令查找网络交换机
        try:
            output = subprocess.run(
                ['lspci', '-nn', '-d', '0x0207:'],  # 0x0207是网络交换机设备ID
                capture_output=True,
                text=True
            )
            if output.returncode == 0:
                lines = output.stdout.split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split(':')
                        if len(parts) >= 3:
                            pci_address = parts[0].strip()
                            switch_info = parts[2].strip()

                            # 提取厂商和型号
                            vendor = 'Unknown'
                            model = switch_info
                            if '[' in switch_info and ']' in switch_info:
                                vendor_part = switch_info.split('[')[1].split(']')[0]
                                vendor = vendor_part
                                model = switch_info.split(']')[1].strip()

                            switch = {
                                'model': model,
                                'vendor': vendor,
                                'ports': 'Unknown',
                                'state': 'Present',
                                'identifier': pci_address,
                                'type': 'Onboard Switch',
                                'pci_address': pci_address
                            }
                            onboard_switches.append(switch)
        except subprocess.SubprocessError:
            pass

        # 尝试查找常见的板载交换机芯片
        try:
            output = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
            if output.returncode == 0:
                lines = output.stdout.split('\n')
                for line in lines:
                    if line.strip() and ('switch' in line.lower() or 'hub' in line.lower()):
                        parts = line.split(':')
                        if len(parts) >= 3:
                            pci_address = parts[0].strip()
                            switch_info = parts[2].strip()

                            vendor = 'Unknown'
                            model = switch_info
                            if '[' in switch_info and ']' in switch_info:
                                vendor_part = switch_info.split('[')[1].split(']')[0]
                                vendor = vendor_part
                                model = switch_info.split(']')[1].strip()

                            # 检查是否已经存在
                            existing = False
                            for switch in onboard_switches:
                                if switch.get('identifier') == pci_address:
                                    existing = True
                                    break
                            if not existing:
                                switch = {
                                    'model': model,
                                    'vendor': vendor,
                                    'ports': 'Unknown',
                                    'state': 'Present',
                                    'identifier': pci_address,
                                    'type': 'Onboard Switch',
                                    'pci_address': pci_address
                                }
                                onboard_switches.append(switch)
        except subprocess.SubprocessError:
            pass

        # 尝试从/sys获取板载交换机信息
        try:
            if os.path.exists('/sys/class/net'):
                for dev in os.listdir('/sys/class/net'):
                    if dev != 'lo':
                        try:
                            if os.path.exists(f'/sys/class/net/{dev}/device'):
                                # 检查是否为交换机设备
                                try:
                                    with open(f'/sys/class/net/{dev}/device/device', 'r') as f:
                                        device_id = f.read().strip()
                                    with open(f'/sys/class/net/{dev}/device/vendor', 'r') as f:
                                        vendor_id = f.read().strip()

                                    # 检查是否为交换机设备
                                    if device_id and vendor_id:
                                        # 这里可以添加更多的设备ID判断
                                        switch = {
                                            'model': f"Network Device ({dev})",
                                            'vendor': vendor_id,
                                            'ports': 'Unknown',
                                            'state': 'Present',
                                            'identifier': dev,
                                            'type': 'Onboard Switch',
                                            'device_id': device_id
                                        }
                                        onboard_switches.append(switch)
                                except Exception:
                                    pass
                        except Exception:
                            pass
        except Exception:
            pass

        return onboard_switches

    except Exception as e:
        logger.error(f'获取板载交换机信息失败: {e}')
        return []
