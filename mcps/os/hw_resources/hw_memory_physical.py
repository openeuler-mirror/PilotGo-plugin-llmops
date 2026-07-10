import logging
import os
import platform
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_mem_physical')

def fetch_hw_mem_physical(mem_type=None):
    """
    采集物理内存信息

    参数:
        mem_type: 信息类型，可选值：
            - 'total': 总容量
            - 'model': 内存型号
            - 'vendor': 厂商
            - 'frequency': 频率
            - 'slots': 插槽数
            - 'installed': 已插插槽
            - None: 获取所有信息

    返回:
        格式化的物理内存信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 物理内存信息 ===')

        # 获取物理内存信息
        mem_data = fetch_physical_memory_details()

        # 根据参数返回不同信息
        if mem_type == 'total':
            total = mem_data.get('total', 'Unknown')
            return f"物理内存总容量: {total}"
        elif mem_type == 'model':
            models = mem_data.get('models', [])
            if models:
                model_info = '\n'.join([f"  插槽 {i}: {model}" for i, model in enumerate(models)])
                return f"内存型号:\n{model_info}"
            else:
                return "内存型号: 未知"
        elif mem_type == 'vendor':
            vendors = mem_data.get('vendors', [])
            if vendors:
                vendor_info = '\n'.join([f"  插槽 {i}: {vendor}" for i, vendor in enumerate(vendors)])
                return f"内存厂商:\n{vendor_info}"
            else:
                return "内存厂商: 未知"
        elif mem_type == 'frequency':
            frequencies = mem_data.get('frequencies', [])
            if frequencies:
                freq_info = '\n'.join([f"  插槽 {i}: {freq}" for i, freq in enumerate(frequencies)])
                return f"内存频率:\n{freq_info}"
            else:
                return "内存频率: 未知"
        elif mem_type == 'slots':
            slots = mem_data.get('slots', 'Unknown')
            slots_note = mem_data.get('slots_note', '')
            return f"内存插槽数: {slots}{slots_note}"
        elif mem_type == 'installed':
            installed = mem_data.get('installed', 'Unknown')
            return f"已插内存数: {installed}"
        else:
            # 获取所有信息
            output.append(f"物理内存总容量: {mem_data.get('total', 'Unknown')}")
            slots_note = mem_data.get('slots_note', '')
            output.append(f"内存插槽数: {mem_data.get('slots', 'Unknown')}{slots_note}")
            output.append(f"已插内存数: {mem_data.get('installed', 'Unknown')}")
            output.append(f"可用插槽数: {mem_data.get('available', 'Unknown')}")

            # 内存详细信息
            memory_details = mem_data.get('details', [])
            if memory_details:
                output.append("\n内存详细信息:")
                for i, detail in enumerate(memory_details):
                    output.append(f"  插槽 {i}:")
                    output.append(f"    容量: {detail.get('size', 'Unknown')}")
                    output.append(f"    型号: {detail.get('model', 'Unknown')}")
                    output.append(f"    厂商: {detail.get('vendor', 'Unknown')}")
                    output.append(f"    频率: {detail.get('frequency', 'Unknown')}")
                    output.append(f"    类型: {detail.get('type', 'Unknown')}")
                    output.append(f"    速度: {detail.get('speed', 'Unknown')}")
                    output.append(f"    电压: {detail.get('voltage', 'Unknown')}")

            # 内存使用情况
            try:
                memory_usage = fetch_memory_usage()
                if memory_usage:
                    output.append("\n内存使用情况:")
                    for line in memory_usage.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取内存使用情况失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取物理内存信息失败: {e}')
        return f'获取物理内存信息失败: {e}'
