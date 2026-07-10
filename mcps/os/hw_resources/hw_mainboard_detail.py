import logging
import os
import platform
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_mobo_info')

def fetch_hw_mobo_info(mobo_type=None):
    """
    采集主板信息

    参数:
        mobo_type: 信息类型，可选值：
            - 'model': 主板型号
            - 'vendor': 主板厂商
            - 'chipset': 芯片组
            - 'serial': 主板序列号
            - 'max_memory': 支持的内存最大容量
            - 'form_factor': 主板规格
            - None: 获取所有信息

    返回:
        格式化的主板信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 主板信息 ===')

        # 获取主板信息
        mobo_info = fetch_mobo_details()

        # 根据参数返回不同信息
        if mobo_type == 'model':
            model = mobo_info.get('model', 'Unknown')
            return f"主板型号: {model}"
        elif mobo_type == 'vendor':
            vendor = mobo_info.get('vendor', 'Unknown')
            return f"主板厂商: {vendor}"
        elif mobo_type == 'chipset':
            chipset = mobo_info.get('chipset', 'Unknown')
            return f"芯片组: {chipset}"
        elif mobo_type == 'serial':
            serial = mobo_info.get('serial', 'Unknown')
            return f"主板序列号: {serial}"
        elif mobo_type == 'max_memory':
            max_memory = mobo_info.get('max_memory', 'Unknown')
            return f"支持的内存最大容量: {max_memory}"
        elif mobo_type == 'form_factor':
            form_factor = mobo_info.get('form_factor', 'Unknown')
            return f"主板规格: {form_factor}"
        else:
            # 获取所有信息
            output.append(f"主板厂商: {mobo_info.get('vendor', 'Unknown')}")
            output.append(f"主板型号: {mobo_info.get('model', 'Unknown')}")
            output.append(f"主板序列号: {mobo_info.get('serial', 'Unknown')}")
            output.append(f"芯片组: {mobo_info.get('chipset', 'Unknown')}")
            output.append(f"主板规格: {mobo_info.get('form_factor', 'Unknown')}")
            output.append(f"支持的内存最大容量: {mobo_info.get('max_memory', 'Unknown')}")
            output.append(f"内存插槽数: {mobo_info.get('memory_slots', 'Unknown')}")

            # 主板扩展信息
            try:
                extended_info = fetch_mobo_extended_info()
                if extended_info:
                    output.append("\n主板扩展信息:")
                    for line in extended_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取主板扩展信息失败: {e}')

            # 主板接口信息
            try:
                interface_info = fetch_mobo_interface_info()
                if interface_info:
                    output.append("\n主板接口信息:")
                    for line in interface_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取主板接口信息失败: {e}')

            # 主板PCI设备信息
            try:
                pci_info = fetch_mobo_pci_info()
                if pci_info:
                    output.append("\n主板PCI设备信息:")
                    for line in pci_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取主板PCI设备信息失败: {e}')

            # 主板SATA设备信息
            try:
                sata_info = fetch_mobo_sata_info()
                if sata_info:
                    output.append("\n主板SATA设备信息:")
                    for line in sata_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取主板SATA设备信息失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取主板信息失败: {e}')
        return f'获取主板信息失败: {e}'
