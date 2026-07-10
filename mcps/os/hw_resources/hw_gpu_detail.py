import logging
import os
import platform
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(label)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_video_info')

def fetch_hw_video_info(video_type=None):
    """
    采集显卡/视频卡信息

    参数:
        video_type: 信息类型，可选值：
            - 'model': 显卡型号
            - 'vendor': 显卡厂商
            - 'memory': 显存大小
            - 'driver': 驱动版本
            - 'interface': 显示输出接口
            - None: 获取所有信息

    返回:
        格式化的显卡/视频卡信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 显卡/视频卡信息 ===')

        # 获取显卡/视频卡信息
        video_info = fetch_video_details()

        # 根据参数返回不同信息
        if video_type == 'model':
            models = video_info.get('models', [])
            if models:
                model_info = '\n'.join([f"  显卡 {i}: {model}" for i, model in enumerate(models)])
                return f"显卡型号:\n{model_info}"
            else:
                return "显卡型号: 未检测到显卡"
        elif video_type == 'vendor':
            vendors = video_info.get('vendors', [])
            if vendors:
                vendor_info = '\n'.join([f"  显卡 {i}: {vendor}" for i, vendor in enumerate(vendors)])
                return f"显卡厂商:\n{vendor_info}"
            else:
                return "显卡厂商: 未检测到显卡"
        elif video_type == 'memory':
            memories = video_info.get('memories', [])
            if memories:
                memory_info = '\n'.join([f"  显卡 {i}: {memory}" for i, memory in enumerate(memories)])
                return f"显存大小:\n{memory_info}"
            else:
                return "显存大小: 未检测到显卡"
        elif video_type == 'driver':
            drivers = video_info.get('drivers', [])
            if drivers:
                driver_info = '\n'.join([f"  显卡 {i}: {driver}" for i, driver in enumerate(drivers)])
                return f"驱动版本:\n{driver_info}"
            else:
                return "驱动版本: 未检测到显卡"
        elif video_type == 'interface':
            interfaces = video_info.get('interfaces', [])
            if interfaces:
                interface_info = '\n'.join([f"  显卡 {i}: {interface}" for i, interface in enumerate(interfaces)])
                return f"显示输出接口:\n{interface_info}"
            else:
                return "显示输出接口: 未检测到显卡"
        else:
            # 获取所有信息
            total_cards = len(video_info.get('models', []))
            output.append(f"检测到显卡数量: {total_cards}")

            # 显卡详细信息
            video_cards = video_info.get('video_cards', [])
            if video_cards:
                output.append("\n显卡详细信息:")
                for i, card in enumerate(video_cards):
                    output.append(f"  显卡 {i}:")
                    output.append(f"    型号: {card.get('model', 'Unknown')}")
                    output.append(f"    厂商: {card.get('vendor', 'Unknown')}")
                    output.append(f"    显存大小: {card.get('memory', 'Unknown')}")
                    output.append(f"    驱动版本: {card.get('driver', 'Unknown')}")
                    output.append(f"    驱动日期: {card.get('driver_date', 'Unknown')}")
                    output.append(f"    显示输出接口: {card.get('interface', 'Unknown')}")
                    output.append(f"    PCI地址: {card.get('pci_address', 'Unknown')}")
                    output.append(f"    设备ID: {card.get('device_id', 'Unknown')}")
                    output.append(f"    状态: {card.get('status', 'Unknown')}")

            # 显示器信息
            monitors = video_info.get('monitors', [])
            if monitors:
                output.append("\n显示器信息:")
                for i, monitor in enumerate(monitors):
                    output.append(f"  显示器 {i}:")
                    output.append(f"    名称: {monitor.get('label', 'Unknown')}")
                    output.append(f"    分辨率: {monitor.get('resolution', 'Unknown')}")
                    output.append(f"    刷新率: {monitor.get('refresh_rate', 'Unknown')}")
                    output.append(f"    连接接口: {monitor.get('connection', 'Unknown')}")

            # OpenGL信息
            try:
                opengl_info = fetch_opengl_info()
                if opengl_info:
                    output.append("\nOpenGL信息:")
                    for line in opengl_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取OpenGL信息失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取显卡/视频卡信息失败: {e}')
        return f'获取显卡/视频卡信息失败: {e}'
def fetch_video_details():
    """
    获取显卡/视频卡详细信息

    返回:
        显卡/视频卡详细信息字典
    """
    try:
        video_info = {
            'models': [],
            'vendors': [],
            'memories': [],
            'drivers': [],
            'interfaces': [],
            'video_cards': [],
            'monitors': []
        }

        if platform.system() == 'Linux':
            # 尝试使用lspci命令获取显卡信息
            try:
                output = subprocess.run(
                    ['lspci', '-vmm', '-d', '0x0300:'],  # 0x0300是显示控制器设备ID
                    capture_output=True,
                    text=True
                )
                if output.returncode == 0:
                    linux_video_cards = analyze_lspci_video(output.stdout)
                    for card in linux_video_cards:
                        video_info['video_cards'].append(card)
                        video_info['models'].append(card.get('model', 'Unknown'))
                        video_info['vendors'].append(card.get('vendor', 'Unknown'))
                        video_info['memories'].append(card.get('memory', 'Unknown'))
                        video_info['drivers'].append(card.get('driver', 'Unknown'))
                        video_info['interfaces'].append(card.get('interface', 'Unknown'))
            except subprocess.SubprocessError:
                pass

            # 尝试使用glxinfo命令获取OpenGL信息
            try:
                output = subprocess.run(['glxinfo', '-B'], capture_output=True, text=True)
                if output.returncode == 0:
                    glx_info = analyze_glxinfo(output.stdout)
                    if glx_info:
                        # 更新显卡信息
                        for i, card in enumerate(video_info['video_cards']):
                            if 'driver' in glx_info:
                                video_info['drivers'][i] = glx_info['driver']
                            if 'renderer' in glx_info:
                                video_info['models'][i] = glx_info['renderer']
            except subprocess.SubprocessError:
                pass

            # 尝试从/sys获取显卡信息
            try:
                if os.path.exists('/sys/class/drm'):
                    drm_devices = os.listdir('/sys/class/drm')
                    for dev in drm_devices:
                        if dev.startswith('card') and '-' not in dev:
                            try:
                                card_info = fetch_video_info_from_sys(dev)
                                if card_info:
                                    # 检查是否已经存在该显卡
                                    existing = False
                                    for card in video_info['video_cards']:
                                        if card.get('pci_address') == card_info.get('pci_address'):
                                            existing = True
                                            break
                                    if not existing:
                                        video_info['video_cards'].append(card_info)
                                        video_info['models'].append(card_info.get('model', 'Unknown'))
                                        video_info['vendors'].append(card_info.get('vendor', 'Unknown'))
                                        video_info['memories'].append(card_info.get('memory', 'Unknown'))
                                        video_info['drivers'].append(card_info.get('driver', 'Unknown'))
                                        video_info['interfaces'].append(card_info.get('interface', 'Unknown'))
                            except Exception:
                                pass
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                output = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
                if output.returncode == 0:
                    mac_video_cards = analyze_macos_video(output.stdout)
                    for card in mac_video_cards:
                        video_info['video_cards'].append(card)
                        video_info['models'].append(card.get('model', 'Unknown'))
                        video_info['vendors'].append(card.get('vendor', 'Unknown'))
                        video_info['memories'].append(card.get('memory', 'Unknown'))
                        video_info['drivers'].append(card.get('driver', 'Unknown'))
                        video_info['interfaces'].append(card.get('interface', 'Unknown'))
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                output = subprocess.run(['wmic', 'path', 'Win32_VideoController', 'get', 'Name,AdapterRAM,DriverVersion,DriverDate,PNPDeviceID,Status'], capture_output=True, text=True)
                if output.returncode == 0:
                    windows_video_cards = analyze_windows_video(output.stdout)
                    for card in windows_video_cards:
                        video_info['video_cards'].append(card)
                        video_info['models'].append(card.get('model', 'Unknown'))
                        video_info['vendors'].append(card.get('vendor', 'Unknown'))
                        video_info['memories'].append(card.get('memory', 'Unknown'))
                        video_info['drivers'].append(card.get('driver', 'Unknown'))
                        video_info['interfaces'].append(card.get('interface', 'Unknown'))
            except subprocess.SubprocessError:
                pass

        # 获取显示器信息
        try:
            monitors = fetch_monitor_info()
            if monitors:
                video_info['monitors'] = monitors
        except Exception as e:
            logger.warning(f'获取显示器信息失败: {e}')

        return video_info

    except Exception as e:
        logger.error(f'获取显卡/视频卡详细信息失败: {e}')
        return {
            'models': [],
            'vendors': [],
            'memories': [],
            'drivers': [],
            'interfaces': [],
            'video_cards': [],
            'monitors': []
        }
def analyze_lspci_video(output):
    """
    解析lspci命令输出中的显卡信息

    参数:
        output: lspci命令输出

    返回:
        显卡信息列表
    """
    try:
        video_cards = []
        current_card = {}

        lines = output.split('\n')
        for line in lines:
            if line.strip():
                if ':' in line:
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()

                    if key == 'Slot':
                        if current_card:
                            video_cards.append(current_card)
                        current_card = {
                            'model': 'Unknown',
                            'vendor': 'Unknown',
                            'memory': 'Unknown',
                            'driver': 'Unknown',
                            'interface': 'Unknown',
                            'pci_address': val,
                            'device_id': 'Unknown',
                            'driver_date': 'Unknown',
                            'status': 'Unknown'
                        }
                    elif key == 'Vendor':
                        current_card['vendor'] = val
                    elif key == 'Device':
                        current_card['model'] = val
                    elif key == 'Driver':
                        current_card['driver'] = val
            elif current_card:
                video_cards.append(current_card)
                current_card = {}

        if current_card:
            video_cards.append(current_card)

        # 补充显存信息
        for card in video_cards:
            pci_address = card.get('pci_address')
            if pci_address:
                try:
                    # 尝试从/sys获取显存大小
                    if os.path.exists(f'/sys/bus/pci/devices/{pci_address}/resource'):
                        with open(f'/sys/bus/pci/devices/{pci_address}/resource', 'r') as f:
                            lines = f.readlines()
                            if lines:
                                # 简单估算显存大小
                                card['memory'] = 'Unknown'
                except Exception:
                    pass

        return video_cards

    except Exception as e:
        logger.error(f'解析lspci显卡输出失败: {e}')
        return []
def analyze_glxinfo(output):
    """
    解析glxinfo命令输出

    参数:
        output: glxinfo命令输出

    返回:
        OpenGL信息字典
    """
    try:
        glx_info = {}

        lines = output.split('\n')
        for line in lines:
            if 'OpenGL renderer string:' in line:
                glx_info['renderer'] = line.split(':', 1)[1].strip()
            elif 'OpenGL vendor string:' in line:
                glx_info['vendor'] = line.split(':', 1)[1].strip()
            elif 'OpenGL version string:' in line:
                glx_info['version'] = line.split(':', 1)[1].strip()
            elif 'OpenGL driver version:' in line:
                glx_info['driver'] = line.split(':', 1)[1].strip()

        return glx_info

    except Exception as e:
        logger.error(f'解析glxinfo输出失败: {e}')
        return {}
def fetch_video_info_from_sys(card_name):
    """
    从/sys获取显卡信息

    参数:
        card_name: 显卡名称

    返回:
        显卡信息字典
    """
    try:
        card_info = {
            'model': card_name,
            'vendor': 'Unknown',
            'memory': 'Unknown',
            'driver': 'Unknown',
            'interface': 'Unknown',
            'pci_address': 'Unknown',
            'device_id': 'Unknown',
            'driver_date': 'Unknown',
            'status': 'Unknown'
        }

        card_path = f'/sys/class/drm/{card_name}/device'
        if os.path.exists(card_path):
            # 获取PCI地址
            try:
                pci_address = os.path.basename(os.path.realpath(card_path))
                card_info['pci_address'] = pci_address
            except Exception:
                pass

            # 获取厂商和设备ID
            try:
                with open(f'{card_path}/vendor', 'r') as f:
                    vendor_id = f.read().strip()
                    card_info['vendor'] = vendor_id
            except Exception:
                pass

            try:
                with open(f'{card_path}/device', 'r') as f:
                    device_id = f.read().strip()
                    card_info['device_id'] = device_id
            except Exception:
                pass

            # 获取驱动信息
            try:
                if os.path.exists(f'{card_path}/driver'):
                    driver_link = os.readlink(f'{card_path}/driver')
                    driver_name = os.path.basename(driver_link)
                    card_info['driver'] = driver_name
            except Exception:
                pass

            # 获取状态
            try:
                with open(f'{card_path}/enable', 'r') as f:
                    enable = f.read().strip()
                    card_info['status'] = 'Enabled' if enable == '1' else 'Disabled'
            except Exception:
                pass

        return card_info

    except Exception as e:
        logger.error(f'从/sys获取显卡信息失败: {e}')
        return None
def fetch_monitor_info():
    """
    获取显示器信息

    返回:
        显示器信息列表
    """
    try:
        monitors = []

        if platform.system() == 'Linux':
            try:
                output = subprocess.run(['xrandr', '--verbose'], capture_output=True, text=True)
                if output.returncode == 0:
                    linux_monitors = analyze_xrandr_output(output.stdout)
                    monitors.extend(linux_monitors)
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Darwin':
            try:
                output = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True)
                if output.returncode == 0:
                    mac_monitors = analyze_macos_monitor(output.stdout)
                    monitors.extend(mac_monitors)
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            try:
                output = subprocess.run(['wmic', 'path', 'Win32_DesktopMonitor', 'get', 'Name,ScreenWidth,ScreenHeight,PNPDeviceID'], capture_output=True, text=True)
                if output.returncode == 0:
                    windows_monitors = analyze_windows_monitor(output.stdout)
                    monitors.extend(windows_monitors)
            except subprocess.SubprocessError:
                pass

        return monitors

    except Exception as e:
        logger.error(f'获取显示器信息失败: {e}')
        return []
def analyze_xrandr_output(output):
    """
    解析xrandr命令输出

    参数:
        output: xrandr命令输出

    返回:
        显示器信息列表
    """
    try:
        monitors = []
        current_monitor = {}

        lines = output.split('\n')
        for line in lines:
            if ' connected' in line:
                if current_monitor:
                    monitors.append(current_monitor)

                parts = line.split(' ')
                monitor_name = parts[0]
                current_monitor = {
                    'label': monitor_name,
                    'resolution': 'Unknown',
                    'refresh_rate': 'Unknown',
                    'connection': 'Unknown'
                }

                # 解析分辨率
                for part in parts:
                    if 'x' in part and '+' in part:
                        resolution = part.split('+')[0]
                        current_monitor['resolution'] = resolution
            elif current_monitor and 'Refresh rate:' in line:
                refresh_rate = line.split(':', 1)[1].strip()
                current_monitor['refresh_rate'] = refresh_rate

        if current_monitor:
            monitors.append(current_monitor)

        return monitors

    except Exception as e:
        logger.error(f'解析xrandr输出失败: {e}')
        return []
def fetch_opengl_info():
    """
    获取OpenGL信息

    返回:
        OpenGL信息字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                output = subprocess.run(['glxinfo', '-B'], capture_output=True, text=True)
                if output.returncode == 0:
                    return output.stdout
            except subprocess.SubprocessError:
                pass

        return None

    except Exception as e:
        logger.error(f'获取OpenGL信息失败: {e}')
        return None
def analyze_macos_video(output):
    """
    解析macOS system_profiler输出

    参数:
        output: system_profiler命令输出

    返回:
        显卡信息列表
    """
    try:
        video_cards = []
        current_card = {}

        lines = output.split('\n')
        for line in lines:
            if line.strip() and ':' in line:
                parts = line.split(':', 1)
                key = parts[0].strip()
                val = parts[1].strip()

                if 'Graphics/Displays' in key:
                    if current_card:
                        video_cards.append(current_card)
                    current_card = {
                        'model': 'Unknown',
                        'vendor': 'Apple',
                        'memory': 'Unknown',
                        'driver': 'Unknown',
                        'interface': 'Unknown',
                        'pci_address': 'Unknown',
                        'device_id': 'Unknown',
                        'driver_date': 'Unknown',
                        'status': 'Unknown'
                    }
                elif current_card:
                    if 'Chipset Model' in key:
                        current_card['model'] = val
                    elif 'VRAM (Total)' in key:
                        current_card['memory'] = val
                    elif 'Vendor' in key:
                        current_card['vendor'] = val
                    elif 'Device ID' in key:
                        current_card['device_id'] = val
                    elif 'Revision ID' in key:
                        current_card['revision'] = val

        if current_card:
            video_cards.append(current_card)

        return video_cards

    except Exception as e:
        logger.error(f'解析macOS显卡输出失败: {e}')
        return []
