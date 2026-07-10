import logging
import os
import platform
import re
import subprocess
import traceback

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(label)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_mem_virtual')

def fetch_hw_mem_virtual(vmem_type=None):
    """
    采集虚拟内存基础配置

    参数:
        vmem_type: 信息类型，可选值：
            - 'swap': 交换分区配置
            - 'page_size': 内存页大小
            - 'address_bits': 地址位数
            - 'swap_total': 交换分区总大小
            - 'swap_used': 交换分区已用大小
            - 'swap_free': 交换分区空闲大小
            - None: 获取所有信息

    返回:
        格式化的虚拟内存基础配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 虚拟内存基础配置 ===')

        # 获取虚拟内存基础配置
        vmem_info = fetch_virtual_memory_details()

        # 根据参数返回不同信息
        if vmem_type == 'swap':
            swap_info = vmem_info.get('swap', {})
            if swap_info:
                swap_str = render_swap_info(swap_info)
                return f"交换分区配置:\n{swap_str}"
            else:
                return "交换分区配置: 未知"
        elif vmem_type == 'page_size':
            page_size = vmem_info.get('page_size', 'Unknown')
            return f"内存页大小: {page_size}"
        elif vmem_type == 'address_bits':
            address_bits = vmem_info.get('address_bits', 'Unknown')
            return f"地址位数: {address_bits}"
        elif vmem_type == 'swap_total':
            swap_total = vmem_info.get('swap_total', 'Unknown')
            return f"交换分区总大小: {swap_total}"
        elif vmem_type == 'swap_used':
            swap_used = vmem_info.get('swap_used', 'Unknown')
            return f"交换分区已用大小: {swap_used}"
        elif vmem_type == 'swap_free':
            swap_free = vmem_info.get('swap_free', 'Unknown')
            return f"交换分区空闲大小: {swap_free}"
        else:
            # 获取所有信息
            output.append(f"内存页大小: {vmem_info.get('page_size', 'Unknown')}")
            output.append(f"地址位数: {vmem_info.get('address_bits', 'Unknown')}")
            output.append(f"虚拟地址空间大小: {vmem_info.get('virtual_address_space', 'Unknown')}")
            output.append(f"物理地址空间大小: {vmem_info.get('physical_address_space', 'Unknown')}")

            # 交换分区信息
            swap_info = vmem_info.get('swap', {})
            if swap_info:
                output.append("\n交换分区配置:")
                swap_str = render_swap_info(swap_info)
                for line in swap_str.split('\n'):
                    output.append(f"  {line}")

            # 交换分区使用情况
            try:
                swap_usage = fetch_swap_usage()
                if swap_usage:
                    output.append("\n交换分区使用情况:")
                    for line in swap_usage.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取交换分区使用情况失败: {e}')

            # 虚拟内存管理信息
            try:
                vmm_info = fetch_virtual_memory_management()
                if vmm_info:
                    output.append("\n虚拟内存管理信息:")
                    for line in vmm_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取虚拟内存管理信息失败: {e}')

            # 内存映射信息
            try:
                mmap_info = fetch_memory_mapping_info()
                if mmap_info:
                    output.append("\n内存映射信息:")
                    for line in mmap_info.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取内存映射信息失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取虚拟内存基础配置失败: {e}')
        return f'获取虚拟内存基础配置失败: {e}'
