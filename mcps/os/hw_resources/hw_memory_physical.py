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
def fetch_physical_memory_details():
    """
    获取物理内存详细信息

    返回:
        物理内存详细信息字典
    """
    try:
        mem_data = {
            'total': 'Unknown',
            'slots': 'Unknown',
            'installed': 'Unknown',
            'available': 'Unknown',
            'models': [],
            'vendors': [],
            'frequencies': [],
            'details': []
        }

        if platform.system() == 'Linux':
            # 尝试从/proc/meminfo获取总内存
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            total_kb = int(line.split()[1])
                            total_gb = total_kb / 1024 / 1024
                            mem_data['total'] = f"{total_gb:.2f} GB"
                            break
            except Exception:
                pass

            # 尝试使用dmidecode命令获取内存信息
            try:
                output = subprocess.run(['sudo', 'dmidecode', '-t', 'memory'], capture_output=True, text=True)
                if output.returncode == 0:
                    mem_data = analyze_dmidecode_memory(output.stdout, mem_data)
            except subprocess.SubprocessError:
                pass

            # 尝试使用lshw命令获取内存信息
            try:
                output = subprocess.run(['sudo', 'lshw', '-class', 'memory'], capture_output=True, text=True)
                if output.returncode == 0:
                    mem_data = analyze_lshw_memory(output.stdout, mem_data)
            except subprocess.SubprocessError:
                pass

            # 尝试从/sys/devices/system/memory获取内存信息
            try:
                memory_blocks = os.listdir('/sys/devices/system/memory')
                # 只计算以memory开头的目录
                memory_dirs = [block for block in memory_blocks if block.startswith('memory') and os.path.isdir(f'/sys/devices/system/memory/{block}')]
                if memory_dirs:
                    mem_data['slots'] = str(len(memory_dirs))
                    mem_data['slots_note'] = '（注：此为内存块数量，非物理插槽数）'
                    installed = 0
                    for block in memory_dirs:
                        state_file = f'/sys/devices/system/memory/{block}/state'
                        if os.path.exists(state_file):
                            with open(state_file, 'r') as f:
                                if 'online' in f.read():
                                    installed += 1
                    mem_data['installed'] = str(installed)
                    if mem_data['slots'] != 'Unknown':
                        mem_data['available'] = str(int(mem_data['slots']) - installed)
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                # 获取内存总容量
                output = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
                if output.returncode == 0:
                    total_bytes = int(output.stdout.strip())
                    total_gb = total_bytes / 1024 / 1024 / 1024
                    mem_data['total'] = f"{total_gb:.2f} GB"

                # 获取内存详细信息
                output = subprocess.run(['system_profiler', 'SPMemoryDataType'], capture_output=True, text=True)
                if output.returncode == 0:
                    mem_data = analyze_macos_memory(output.stdout, mem_data)
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                # 获取内存总容量
                output = subprocess.run(['wmic', 'memorychip', 'get', 'Capacity'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.strip().split('\n')[1:]
                    total_bytes = 0
                    for line in lines:
                        if line.strip():
                            total_bytes += int(line.strip())
                    total_gb = total_bytes / 1024 / 1024 / 1024
                    mem_data['total'] = f"{total_gb:.2f} GB"

                # 获取内存详细信息
                output = subprocess.run(['wmic', 'memorychip', 'get', 'Capacity,Manufacturer,PartNumber,Speed,ConfiguredClockSpeed'], capture_output=True, text=True)
                if output.returncode == 0:
                    mem_data = analyze_windows_memory(output.stdout, mem_data)
            except subprocess.SubprocessError:
                pass

        return mem_data

    except Exception as e:
        logger.error(f'获取物理内存详细信息失败: {e}')
        return {
            'total': 'Unknown',
            'slots': 'Unknown',
            'installed': 'Unknown',
            'available': 'Unknown',
            'models': [],
            'vendors': [],
            'frequencies': [],
            'details': []
        }
def analyze_dmidecode_memory(output, mem_data):
    """
    解析dmidecode内存输出

    参数:
        output: dmidecode输出
        mem_data: 内存信息字典

    返回:
        更新后的内存信息字典
    """
    try:
        lines = output.split('\n')
        current_device = None
        devices = []

        for line in lines:
            line = line.strip()
            if line.startswith('Memory Device'):
                if current_device:
                    devices.append(current_device)
                current_device = {}
            elif current_device is not None and ':' in line:
                key, val = line.split(':', 1)
                key = key.strip()
                val = val.strip()
                current_device[key] = val

        if current_device:
            devices.append(current_device)

        # 更新内存信息
        installed_count = 0
        for device in devices:
            if device.get('Size', 'No Module Installed') != 'No Module Installed':
                installed_count += 1

                detail = {
                    'size': device.get('Size', 'Unknown'),
                    'model': device.get('Part Number', 'Unknown'),
                    'vendor': device.get('Manufacturer', 'Unknown'),
                    'frequency': device.get('Speed', 'Unknown'),
                    'type': device.get('Type', 'Unknown'),
                    'speed': device.get('Configured Clock Speed', 'Unknown'),
                    'voltage': device.get('Voltage', 'Unknown')
                }
                mem_data['details'].append(detail)
                mem_data['models'].append(detail['model'])
                mem_data['vendors'].append(detail['vendor'])
                mem_data['frequencies'].append(detail['frequency'])

        if devices:
            mem_data['slots'] = str(len(devices))
            mem_data['installed'] = str(installed_count)
            mem_data['available'] = str(len(devices) - installed_count)

        return mem_data

    except Exception as e:
        logger.error(f'解析dmidecode内存输出失败: {e}')
        return mem_data
