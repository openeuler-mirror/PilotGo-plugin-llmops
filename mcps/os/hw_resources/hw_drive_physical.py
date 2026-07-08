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

def fetch_physical_disk_details():
    """
    获取物理磁盘详细信息

    返回:
        物理磁盘详细信息字典
    """
    try:
        disk_info = {
            'models': [],
            'vendors': [],
            'capacities': [],
            'interfaces': [],
            'rpms': [],
            'serials': [],
            'details': []
        }

        if platform.system() == 'Linux':
            # 尝试使用lsblk命令获取磁盘信息
            try:
                output = subprocess.run(['lsblk', '-o', 'NAME,TYPE,SIZE,MODEL,VENDOR,SERIAL,TRAN'], capture_output=True, text=True)
                if output.returncode == 0:
                    disk_info = analyze_lsblk_info(output.stdout, disk_info)
            except subprocess.SubprocessError:
                pass

            # 尝试使用fdisk命令获取磁盘信息
            try:
                output = subprocess.run(['sudo', 'fdisk', '-l'], capture_output=True, text=True)
                if output.returncode == 0:
                    disk_info = analyze_fdisk_info(output.stdout, disk_info)
            except subprocess.SubprocessError:
                pass

            # 尝试从/sys/block获取磁盘信息
            try:
                block_devices = os.listdir('/sys/block')
                for device in block_devices:
                    if device.startswith('sd') or device.startswith('hd') or device.startswith('vd'):
                        disk_detail = fetch_disk_info_from_sys(device)
                        if disk_detail:
                            disk_info['details'].append(disk_detail)
                            disk_info['models'].append(disk_detail.get('model', 'Unknown'))
                            disk_info['vendors'].append(disk_detail.get('vendor', 'Unknown'))
                            disk_info['capacities'].append(disk_detail.get('capacity', 'Unknown'))
                            disk_info['interfaces'].append(disk_detail.get('interface', 'Unknown'))
                            disk_info['rpms'].append(disk_detail.get('rpm', 'Unknown'))
                            disk_info['serials'].append(disk_detail.get('serial', 'Unknown'))
            except Exception:
                pass

            # 尝试使用smartctl命令获取磁盘信息
            try:
                output = subprocess.run(['sudo', 'smartctl', '--scan'], capture_output=True, text=True)
                if output.returncode == 0:
                    for line in output.stdout.split('\n'):
                        if line.strip():
                            device = line.split()[0]
                            disk_detail = fetch_disk_info_from_smartctl(device)
                            if disk_detail:
                                # 检查是否已经存在该设备
                                existing = False
                                for detail in disk_info['details']:
                                    if detail.get('device') == device:
                                        existing = True
                                        break
                                if not existing:
                                    disk_info['details'].append(disk_detail)
                                    disk_info['models'].append(disk_detail.get('model', 'Unknown'))
                                    disk_info['vendors'].append(disk_detail.get('vendor', 'Unknown'))
                                    disk_info['capacities'].append(disk_detail.get('capacity', 'Unknown'))
                                    disk_info['interfaces'].append(disk_detail.get('interface', 'Unknown'))
                                    disk_info['rpms'].append(disk_detail.get('rpm', 'Unknown'))
                                    disk_info['serials'].append(disk_detail.get('serial', 'Unknown'))
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                # 获取磁盘信息
                output = subprocess.run(['diskutil', 'list', '-plist'], capture_output=True, text=True)
                if output.returncode == 0:
                    disk_info = analyze_macos_disk_info(output.stdout, disk_info)
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                # 获取磁盘信息
                output = subprocess.run(['wmic', 'diskdrive', 'get', 'Model,Manufacturer,Size,InterfaceType,SerialNumber,MediaType'], capture_output=True, text=True)
                if output.returncode == 0:
                    disk_info = analyze_windows_disk_info(output.stdout, disk_info)
            except subprocess.SubprocessError:
                pass

        return disk_info

    except Exception as e:
        logger.error(f'获取物理磁盘详细信息失败: {e}')
        return {
            'models': [],
            'vendors': [],
            'capacities': [],
            'interfaces': [],
            'rpms': [],
            'serials': [],
            'details': []
        }

def analyze_lsblk_info(output, disk_info):
    """
    解析lsblk输出

    参数:
        output: lsblk输出
        disk_info: 磁盘信息字典

    返回:
        更新后的磁盘信息字典
    """
    try:
        lines = output.strip().split('\n')[1:]

        for line in lines:
            parts = line.split()
            if len(parts) >= 7 and parts[1] == 'disk':
                device = parts[0]
                size = parts[2]
                model = parts[3]
                vendor = parts[4]
                serial = parts[5]
                interface = parts[6]

                # 构建磁盘详细信息
                detail = {
                    'device': f"/dev/{device}",
                    'model': model,
                    'vendor': vendor,
                    'capacity': size,
                    'interface': interface,
                    'rpm': 'Unknown',
                    'serial': serial,
                    'partitions': 'Unknown'
                }

                disk_info['details'].append(detail)
                disk_info['models'].append(model)
                disk_info['vendors'].append(vendor)
                disk_info['capacities'].append(size)
                disk_info['interfaces'].append(interface)
                disk_info['rpms'].append('Unknown')
                disk_info['serials'].append(serial)

        return disk_info

    except Exception as e:
        logger.error(f'解析lsblk输出失败: {e}')
        return disk_info

def analyze_fdisk_info(output, disk_info):
    """
    解析fdisk输出

    参数:
        output: fdisk输出
        disk_info: 磁盘信息字典

    返回:
        更新后的磁盘信息字典
    """
    try:
        lines = output.split('\n')
        current_device = None
        current_detail = {}

        for line in lines:
            if 'Disk /dev/' in line:
                if current_device and current_detail:
                    disk_info['details'].append(current_detail)
                    disk_info['models'].append(current_detail.get('model', 'Unknown'))
                    disk_info['vendors'].append(current_detail.get('vendor', 'Unknown'))
                    disk_info['capacities'].append(current_detail.get('capacity', 'Unknown'))
                    disk_info['interfaces'].append(current_detail.get('interface', 'Unknown'))
                    disk_info['rpms'].append(current_detail.get('rpm', 'Unknown'))
                    disk_info['serials'].append(current_detail.get('serial', 'Unknown'))

                parts = line.split()
                current_device = parts[1]
                current_detail = {
                    'device': current_device,
                    'model': 'Unknown',
                    'vendor': 'Unknown',
                    'capacity': 'Unknown',
                    'interface': 'Unknown',
                    'rpm': 'Unknown',
                    'serial': 'Unknown',
                    'partitions': '0'
                }

                # 提取容量信息
                if 'GB' in line:
                    capacity = line.split('GB')[0].split('Disk ')[1].strip()
                    current_detail['capacity'] = f"{capacity} GB"
            elif 'Model:' in line:
                model = line.split('Model:')[1].strip()
                current_detail['model'] = model
            elif 'Serial Number:' in line:
                serial = line.split('Serial Number:')[1].strip()
                current_detail['serial'] = serial
            elif 'Disk identifier:' in line:
                identifier = line.split('Disk identifier:')[1].strip()
                current_detail['identifier'] = identifier
            elif 'partitions' in line and 'Device' not in line:
                partitions = line.split()[0]
                current_detail['partitions'] = partitions

        if current_device and current_detail:
            disk_info['details'].append(current_detail)
            disk_info['models'].append(current_detail.get('model', 'Unknown'))
            disk_info['vendors'].append(current_detail.get('vendor', 'Unknown'))
            disk_info['capacities'].append(current_detail.get('capacity', 'Unknown'))
            disk_info['interfaces'].append(current_detail.get('interface', 'Unknown'))
            disk_info['rpms'].append(current_detail.get('rpm', 'Unknown'))
            disk_info['serials'].append(current_detail.get('serial', 'Unknown'))

        return disk_info

    except Exception as e:
        logger.error(f'解析fdisk输出失败: {e}')
        return disk_info

def fetch_disk_info_from_sys(device):
    """
    从/sys 获取磁盘信息

    参数:
        device: 设备名称

    返回:
        磁盘信息字典
    """
    try:
        # 安全校验：验证设备名
        is_valid, error_msg = validate_device_name(device)
        if not is_valid:
            logger.error(f'设备名不合法：{error_msg}')
            return {}

        disk_detail = {
            'device': f"/dev/{device}",
            'model': 'Unknown',
            'vendor': 'Unknown',
            'capacity': 'Unknown',
            'interface': 'Unknown',
            'rpm': 'Unknown',
            'serial': 'Unknown',
            'partitions': 'Unknown'
        }

        # 获取模型信息
        model_path = f"/sys/block/{device}/device/model"
        if os.path.exists(model_path):
            try:
                with open(model_path, 'r') as f:
                    disk_detail['model'] = f.read().strip()
            except Exception:
                pass

        # 获取厂商信息
        vendor_path = f"/sys/block/{device}/device/vendor"
        if os.path.exists(vendor_path):
            try:
                with open(vendor_path, 'r') as f:
                    disk_detail['vendor'] = f.read().strip()
            except Exception:
                pass

        # 获取容量信息
        size_path = f"/sys/block/{device}/size"
        if os.path.exists(size_path):
            try:
                with open(size_path, 'r') as f:
                    sectors = int(f.read().strip())
                    capacity = sectors * 512 / 1024 / 1024 / 1024
                    disk_detail['capacity'] = f"{capacity:.2f} GB"
            except Exception:
                pass

        # 获取分区数
        try:
            partitions = os.listdir(f"/sys/block/{device}")
            partition_count = 0
            for part in partitions:
                if part.startswith(device):
                    partition_count += 1
            disk_detail['partitions'] = str(partition_count)
        except Exception:
            pass

        return disk_detail

    except Exception as e:
        logger.error(f'从/sys获取磁盘信息失败: {e}')
        return {}

def fetch_disk_info_from_smartctl(device):
    """
    从 smartctl 获取磁盘信息

    参数:
        device: 设备路径

    返回:
        磁盘信息字典
    """
    try:
        # 安全校验：验证设备名（处理可能的/dev/前缀）
        device_name = device.replace('/dev/', '') if device.startswith('/dev/') else device
        is_valid, error_msg = validate_device_name(device_name)
        if not is_valid:
            logger.error(f'设备名不合法：{error_msg}')
            return {}

        disk_detail = {
            'device': device,
            'model': 'Unknown',
            'vendor': 'Unknown',
            'capacity': 'Unknown',
            'interface': 'Unknown',
            'rpm': 'Unknown',
            'serial': 'Unknown',
            'partitions': 'Unknown'
        }

        output = subprocess.run(['sudo', 'smartctl', '-i', device], capture_output=True, text=True)

        if output.returncode == 0:
            for line in output.stdout.split('\n'):
                if 'Device Model:' in line:
                    disk_detail['model'] = line.split(':', 1)[1].strip()
                elif 'Vendor:' in line:
                    disk_detail['vendor'] = line.split(':', 1)[1].strip()
                elif 'User Capacity:' in line:
                    capacity = line.split(':', 1)[1].strip()
                    disk_detail['capacity'] = capacity
                elif 'Rotation Rate:' in line:
                    rpm = line.split(':', 1)[1].strip()
                    disk_detail['rpm'] = rpm
                elif 'Serial Number:' in line:
                    disk_detail['serial'] = line.split(':', 1)[1].strip()
                elif 'Transport protocol:' in line:
                    interface = line.split(':', 1)[1].strip()
                    disk_detail['interface'] = interface

        return disk_detail

    except Exception as e:
        logger.error(f'从smartctl获取磁盘信息失败: {e}')
        return {}

def analyze_macos_disk_info(output, disk_info):
    """
    解析macOS磁盘信息

    参数:
        output: diskutil输出
        disk_info: 磁盘信息字典

    返回:
        更新后的磁盘信息字典
    """
    try:
        # 简化处理，实际应该使用plistlib解析
        lines = output.split('\n')
        current_device = None
        current_detail = {}

        for line in lines:
            if '<key>DeviceIdentifier</key>' in line:
                current_device = True
            elif current_device and '<string>' in line:
                device = line.split('<string>')[1].split('</string>')[0]
                current_detail['device'] = device
                current_device = False
            elif '<key>Model</key>' in line:
                current_detail['model'] = 'Unknown'
            elif '<key>Size</key>' in line:
                size = 'Unknown'
                current_detail['capacity'] = size
            elif '<key>Protocol</key>' in line:
                interface = 'Unknown'
                current_detail['interface'] = interface

        if current_detail:
            disk_info['details'].append(current_detail)
            disk_info['models'].append(current_detail.get('model', 'Unknown'))
            disk_info['vendors'].append(current_detail.get('vendor', 'Apple'))
            disk_info['capacities'].append(current_detail.get('capacity', 'Unknown'))
            disk_info['interfaces'].append(current_detail.get('interface', 'Unknown'))
            disk_info['rpms'].append(current_detail.get('rpm', 'Unknown'))
            disk_info['serials'].append(current_detail.get('serial', 'Unknown'))

        return disk_info

    except Exception as e:
        logger.error(f'解析macOS磁盘信息失败: {e}')
        return disk_info

def analyze_windows_disk_info(output, disk_info):
    """
    解析Windows磁盘信息

    参数:
        output: wmic输出
        disk_info: 磁盘信息字典

    返回:
        更新后的磁盘信息字典
    """
    try:
        lines = output.strip().split('\n')[1:]

        for line in lines:
            if line.strip():
                parts = [part.strip() for part in line.split() if part.strip()]
                if len(parts) >= 6:
                    model = ' '.join(parts[1:-4])
                    vendor = parts[0]
                    size = f"{int(parts[-4]) / 1024 / 1024 / 1024:.2f} GB"
                    interface = parts[-3]
                    serial = parts[-2]
                    media = parts[-1]

                    detail = {
                        'device': 'Unknown',
                        'model': model,
                        'vendor': vendor,
                        'capacity': size,
                        'interface': interface,
                        'rpm': 'Unknown',
                        'serial': serial,
                        'partitions': 'Unknown'
                    }

                    disk_info['details'].append(detail)
                    disk_info['models'].append(model)
                    disk_info['vendors'].append(vendor)
                    disk_info['capacities'].append(size)
                    disk_info['interfaces'].append(interface)
                    disk_info['rpms'].append('Unknown')
                    disk_info['serials'].append(serial)

        return disk_info

    except Exception as e:
        logger.error(f'解析Windows磁盘信息失败: {e}')
        return disk_info

def fetch_disk_usage():
    """
    获取磁盘使用情况

    返回:
        磁盘使用情况字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                output = subprocess.run(['df', '-h'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.split('\n')
                    usage_info = []
                    # 保留表头行
                    if lines:
                        usage_info.append(lines[0])  # 添加表头
                    # 添加包含/dev/的数据行
                    for line in lines[1:]:
                        if line.strip() and '/dev/' in line:
                            usage_info.append(line.strip())
                    return '\n'.join(usage_info[:11])  # 包含表头最多11行
            except subprocess.SubprocessError:
                pass

        return ''  # 异常情况下返回空字符串

    except Exception as e:
        logger.error(f'获取磁盘使用情况失败: {e}')
        return ''  # 异常情况下返回空字符串

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_hw_disk_physical",
    "function": fetch_hw_disk_physical,
    "description": "采集物理磁盘信息，包括磁盘型号/厂商/容量/接口(SATA/SAS/SSD)/转速/序列号",
    "parameters": {
        "type": "object",
        "properties": {
            "disk_type": {
                "type": "string",
                "description": "信息类型，可选值：model（磁盘型号）、vendor（磁盘厂商）、capacity（磁盘容量）、interface（磁盘接口）、rpm（磁盘转速）、serial（磁盘序列号），不指定则获取所有信息",
                "enum": ["model", "vendor", "capacity", "interface", "rpm", "serial"]
            }
        },
        "required": []
    }
}
