import logging
import os
import platform
import subprocess

from mcp_tools.cmd_safety_guard import validate_device_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_disk_physical')

def fetch_hw_disk_physical(disk_type=None):
    """
    采集物理磁盘信息

    参数:
        disk_type: 信息类型，可选值：
            - 'model': 磁盘型号
            - 'vendor': 磁盘厂商
            - 'capacity': 磁盘容量
            - 'interface': 磁盘接口
            - 'rpm': 磁盘转速
            - 'serial': 磁盘序列号
            - None: 获取所有信息

    返回:
        格式化的物理磁盘信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 物理磁盘信息 ===')

        # 获取物理磁盘信息
        disk_info = fetch_physical_disk_details()

        # 根据参数返回不同信息
        if disk_type == 'model':
            models = disk_info.get('models', [])
            if models:
                model_info = '\n'.join([f"  磁盘 {i}: {model}" for i, model in enumerate(models)])
                return f"磁盘型号:\n{model_info}"
            else:
                return "磁盘型号: 未知"
        elif disk_type == 'vendor':
            vendors = disk_info.get('vendors', [])
            if vendors:
                vendor_info = '\n'.join([f"  磁盘 {i}: {vendor}" for i, vendor in enumerate(vendors)])
                return f"磁盘厂商:\n{vendor_info}"
            else:
                return "磁盘厂商: 未知"
        elif disk_type == 'capacity':
            capacities = disk_info.get('capacities', [])
            if capacities:
                capacity_info = '\n'.join([f"  磁盘 {i}: {capacity}" for i, capacity in enumerate(capacities)])
                return f"磁盘容量:\n{capacity_info}"
            else:
                return "磁盘容量: 未知"
        elif disk_type == 'interface':
            interfaces = disk_info.get('interfaces', [])
            if interfaces:
                interface_info = '\n'.join([f"  磁盘 {i}: {interface}" for i, interface in enumerate(interfaces)])
                return f"磁盘接口:\n{interface_info}"
            else:
                return "磁盘接口: 未知"
        elif disk_type == 'rpm':
            rpms = disk_info.get('rpms', [])
            if rpms:
                rpm_info = '\n'.join([f"  磁盘 {i}: {rpm}" for i, rpm in enumerate(rpms)])
                return f"磁盘转速:\n{rpm_info}"
            else:
                return "磁盘转速: 未知"
        elif disk_type == 'serial':
            serials = disk_info.get('serials', [])
            if serials:
                serial_info = '\n'.join([f"  磁盘 {i}: {serial}" for i, serial in enumerate(serials)])
                return f"磁盘序列号:\n{serial_info}"
            else:
                return "磁盘序列号: 未知"
        else:
            # 获取所有信息
            output.append(f"检测到磁盘数量: {len(disk_info.get('details', []))}")

            # 磁盘详细信息
            disk_details = disk_info.get('details', [])
            if disk_details:
                output.append("\n磁盘详细信息:")
                for i, detail in enumerate(disk_details):
                    output.append(f"  磁盘 {i}:")
                    output.append(f"    型号: {detail.get('model', 'Unknown')}")
                    output.append(f"    厂商: {detail.get('vendor', 'Unknown')}")
                    output.append(f"    容量: {detail.get('capacity', 'Unknown')}")
                    output.append(f"    接口: {detail.get('interface', 'Unknown')}")
                    output.append(f"    转速: {detail.get('rpm', 'Unknown')}")
                    output.append(f"    序列号: {detail.get('serial', 'Unknown')}")
                    output.append(f"    设备文件: {detail.get('device', 'Unknown')}")
                    output.append(f"    分区数: {detail.get('partitions', 'Unknown')}")

            # 磁盘使用情况
            try:
                disk_usage = fetch_disk_usage()
                if disk_usage:
                    output.append("\n磁盘使用情况:")
                    for line in disk_usage.split('\n'):
                        output.append(f"  {line}")
            except Exception as e:
                logger.warning(f'获取磁盘使用情况失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取物理磁盘信息失败: {e}')
        return f'获取物理磁盘信息失败: {e}'
