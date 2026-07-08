import logging
import os
import platform
import subprocess

from mcp_tools.cmd_safety_guard import validate_device_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_disk_part_table')

def fetch_hw_disk_part_table(part_table_type=None):
    """
    采集磁盘分区表信息

    参数:
        part_table_type: 信息类型，可选值：
            - 'type': 分区表类型（MBR/GPT）
            - 'partitions': 分区信息
            - 'identifier': 分区表标识
            - 'version': 分区表版本
            - 'part_types': 分区类型
            - None: 获取所有信息

    返回:
        格式化的磁盘分区表信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 磁盘分区表信息 ===')

        # 获取磁盘分区表信息
        part_table_info = fetch_partition_table_details()

        # 根据参数返回不同信息
        if part_table_type == 'type':
            table_types = part_table_info.get('table_types', {})
            if table_types:
                type_info = '\n'.join([f"  磁盘 {dev}: {table_type}" for dev, table_type in table_types.items()])
                return f"分区表类型:\n{type_info}"
            else:
                return "分区表类型: 未知"
        elif part_table_type == 'partitions':
            partitions = part_table_info.get('partitions', {})
            if partitions:
                part_info = render_partitions_info(partitions)
                return f"分区信息:\n{part_info}"
            else:
                return "分区信息: 未知"
        elif part_table_type == 'identifier':
            identifiers = part_table_info.get('identifiers', {})
            if identifiers:
                id_info = '\n'.join([f"  磁盘 {dev}: {identifier}" for dev, identifier in identifiers.items()])
                return f"分区表标识:\n{id_info}"
            else:
                return "分区表标识: 未知"
        elif part_table_type == 'version':
            versions = part_table_info.get('versions', {})
            if versions:
                ver_data = '\n'.join([f"  磁盘 {dev}: {version}" for dev, version in versions.items()])
                return f"分区表版本:\n{ver_data}"
            else:
                return "分区表版本: 未知"
        elif part_table_type == 'part_types':
            part_types = part_table_info.get('part_types', {})
            if part_types:
                type_info = render_part_types_info(part_types)
                return f"分区类型:\n{type_info}"
            else:
                return "分区类型: 未知"
        else:
            # 获取所有信息
            output.append(f"检测到磁盘数量: {len(part_table_info.get('devices', []))}")

            # 分区表类型信息
            table_types = part_table_info.get('table_types', {})
            if table_types:
                output.append("\n分区表类型:")
                for dev, table_type in table_types.items():
                    output.append(f"  磁盘 {dev}: {table_type}")

            # 分区表标识信息
            identifiers = part_table_info.get('identifiers', {})
            if identifiers:
                output.append("\n分区表标识:")
                for dev, identifier in identifiers.items():
                    output.append(f"  磁盘 {dev}: {identifier}")

            # 分区表版本信息
            versions = part_table_info.get('versions', {})
            if versions:
                output.append("\n分区表版本:")
                for dev, version in versions.items():
                    output.append(f"  磁盘 {dev}: {version}")

            # 分区详细信息
            partitions = part_table_info.get('partitions', {})
            if partitions:
                output.append("\n分区详细信息:")
                part_info = render_partitions_info(partitions)
                for line in part_info.split('\n'):
                    output.append(f"  {line}")

            # 分区类型信息
            part_types = part_table_info.get('part_types', {})
            if part_types:
                output.append("\n分区类型:")
                type_info = render_part_types_info(part_types)
                for line in type_info.split('\n'):
                    output.append(f"  {line}")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取磁盘分区表信息失败: {e}')
        return f'获取磁盘分区表信息失败: {e}'
