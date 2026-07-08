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
def fetch_partition_table_details():
    """
    获取磁盘分区表详细信息

    返回:
        磁盘分区表详细信息字典
    """
    try:
        part_table_info = {
            'devices': [],
            'table_types': {},  # 设备: 分区表类型
            'identifiers': {},  # 设备: 分区表标识
            'versions': {},     # 设备: 分区表版本
            'partitions': {},   # 设备: 分区列表
            'part_types': {}    # 设备: 分区类型
        }

        if platform.system() == 'Linux':
            # 尝试使用parted命令获取分区表信息
            try:
                # 获取所有磁盘设备
                output = subprocess.run(['lsblk', '-o', 'NAME,TYPE'], capture_output=True, text=True)
                if output.returncode == 0:
                    devices = []
                    for line in output.stdout.split('\n'):
                        parts = line.split()
                        if len(parts) == 2 and parts[1] == 'disk':
                            devices.append(parts[0])

                    # 对每个磁盘获取分区表信息
                    for device in devices:
                        # 安全校验：验证设备名
                        is_valid, error_msg = validate_device_name(device)
                        if not is_valid:
                            logger.warning(f'跳过不合法的设备名 {device}: {error_msg}')
                            continue

                        dev_path = f"/dev/{device}"
                        part_table_info['devices'].append(dev_path)

                        # 使用parted获取分区表信息
                        output = subprocess.run(['sudo', 'parted', '-s', dev_path, 'print'], capture_output=True, text=True)
                        if output.returncode == 0:
                            part_table_info = analyze_parted_output(output.stdout, dev_path, part_table_info)

                        # 使用fdisk获取分区信息
                        output = subprocess.run(['sudo', 'fdisk', '-l', dev_path], capture_output=True, text=True)
                        if output.returncode == 0:
                            part_table_info = analyze_fdisk_output(output.stdout, dev_path, part_table_info)
            except subprocess.SubprocessError:
                pass

            # 尝试从/proc/partitions获取分区信息
            try:
                with open('/proc/partitions', 'r') as f:
                    lines = f.readlines()[2:]  # 跳过前两行表头
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 4:
                            device = parts[3]
                            if not device.endswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
                                # 可能是主设备
                                dev_path = f"/dev/{device}"
                                if dev_path not in part_table_info['devices']:
                                    part_table_info['devices'].append(dev_path)
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                output = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
                if output.returncode == 0:
                    part_table_info = analyze_macos_diskutil_output(output.stdout, part_table_info)
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                output = subprocess.run(['wmic', 'diskdrive', 'get', 'DeviceID,Partitions,Signature'], capture_output=True, text=True)
                if output.returncode == 0:
                    part_table_info = analyze_windows_diskdrive_output(output.stdout, part_table_info)
            except subprocess.SubprocessError:
                pass

        return part_table_info

    except Exception as e:
        logger.error(f'获取磁盘分区表详细信息失败: {e}')
        return {
            'devices': [],
            'table_types': {},
            'identifiers': {},
            'versions': {},
            'partitions': {},
            'part_types': {}
        }
def analyze_parted_output(output, device, part_table_info):
    """
    解析parted命令输出

    参数:
        output: parted命令输出
        device: 设备路径
        part_table_info: 分区表信息字典

    返回:
        更新后的分区表信息字典
    """
    try:
        lines = output.split('\n')
        current_device = device
        partitions = []

        for line in lines:
            line = line.strip()
            if 'Partition Table:' in line:
                table_type = line.split(':', 1)[1].strip()
                part_table_info['table_types'][current_device] = table_type
            elif 'Disk identifier:' in line:
                identifier = line.split(':', 1)[1].strip()
                part_table_info['identifiers'][current_device] = identifier
            elif 'Disk Flags:' in line:
                flags = line.split(':', 1)[1].strip()
                part_table_info['flags'] = flags
            elif line and line[0].isdigit():
                # 分区信息行
                parts = line.split()
                if len(parts) >= 7:
                    # parted输出格式：Number Start End Size File system Name Flags
                    # 最后一列是flags
                    partition = {
                        'number': parts[0],
                        'start': parts[1],
                        'end': parts[2],
                        'size': parts[3],
                        'type': 'Unknown',  # parted输出中没有明确的类型列
                        'file_system': parts[4],  # 第5列是文件系统
                        'flags': parts[-1] if len(parts) > 6 else ''  # 最后一列是标志
                    }
                    partitions.append(partition)
                elif len(parts) >= 5:
                    # 至少有基本信息的情况
                    partition = {
                        'number': parts[0],
                        'start': parts[1],
                        'end': parts[2],
                        'size': parts[3],
                        'type': 'Unknown',
                        'file_system': parts[4] if len(parts) > 4 else 'Unknown',
                        'flags': ''
                    }
                    partitions.append(partition)

        # 确保设备在partitions字典中存在
        if current_device not in part_table_info['partitions']:
            part_table_info['partitions'][current_device] = []

        # 如果有分区数据，则更新
        if partitions:
            part_table_info['partitions'][current_device] = partitions

        return part_table_info

    except Exception as e:
        logger.error(f'解析parted输出失败: {e}')
        return part_table_info
