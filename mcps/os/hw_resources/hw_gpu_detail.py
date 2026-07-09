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
