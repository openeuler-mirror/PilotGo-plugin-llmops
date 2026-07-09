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
