import logging
import os
import platform
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_bios_info')

def fetch_hw_bios_info(bios_type=None):
    """
    采集BIOS/UEFI信息

    参数:
        bios_type: 信息类型，可选值：
            - 'ver': BIOS版本
            - 'vendor': BIOS厂商
            - 'date': 发布日期
            - 'mode': BIOS模式
            - 'uefi': UEFI启动状态
            - 'smbios': SMBIOS版本
            - None: 获取所有信息

    返回:
        格式化的BIOS/UEFI信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== BIOS/UEFI信息 ===')

        # 获取BIOS/UEFI信息
        bios_info = fetch_bios_details()

        # 根据参数返回不同信息
        if bios_type == 'ver':
            ver = bios_info.get('ver', 'Unknown')
            return f"BIOS版本: {ver}"
        elif bios_type == 'vendor':
            vendor = bios_info.get('vendor', 'Unknown')
            return f"BIOS厂商: {vendor}"
        elif bios_type == 'date':
            date = bios_info.get('date', 'Unknown')
            return f"BIOS发布日期: {date}"
        elif bios_type == 'mode':
            mode = bios_info.get('mode', 'Unknown')
            return f"BIOS模式: {mode}"
        elif bios_type == 'uefi':
            uefi = bios_info.get('uefi', 'Unknown')
            return f"UEFI启动状态: {uefi}"
        elif bios_type == 'smbios':
            smbios = bios_info.get('smbios', 'Unknown')
            return f"SMBIOS版本: {smbios}"
        else:
            # 获取所有信息
            output.append(f"BIOS厂商: {bios_info.get('vendor', 'Unknown')}")
            output.append(f"BIOS版本: {bios_info.get('ver', 'Unknown')}")
            output.append(f"BIOS发布日期: {bios_info.get('date', 'Unknown')}")
            output.append(f"BIOS模式: {bios_info.get('mode', 'Unknown')}")
            output.append(f"UEFI启动状态: {bios_info.get('uefi', 'Unknown')}")
            output.append(f"SMBIOS版本: {bios_info.get('smbios', 'Unknown')}")

            # BIOS扩展信息
            try:
                extended_info = fetch_bios_extended_info()
                if extended_info:
                    output.append("\nBIOS扩展信息:")
                    for line in extended_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取BIOS扩展信息失败: {e}')

            # BIOS配置信息
            try:
                cfg_state = fetch_bios_config_info()
                if cfg_state:
                    output.append("\nBIOS配置信息:")
                    for line in cfg_state.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取BIOS配置信息失败: {e}')

            # BIOS安全信息
            try:
                security_info = fetch_bios_security_info()
                if security_info:
                    output.append("\nBIOS安全信息:")
                    for line in security_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取BIOS安全信息失败: {e}')

            # BIOS启动配置
            try:
                boot_info = fetch_bios_boot_info()
                if boot_info:
                    output.append("\nBIOS启动配置:")
                    for line in boot_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取BIOS启动配置失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取BIOS/UEFI信息失败: {e}')
        return f'获取BIOS/UEFI信息失败: {e}'
