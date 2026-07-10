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
def fetch_mobo_details():
    """
    获取主板详细信息

    返回:
        主板详细信息字典
    """
    try:
        mobo_info = {
            'vendor': 'Unknown',
            'model': 'Unknown',
            'serial': 'Unknown',
            'chipset': 'Unknown',
            'form_factor': 'Unknown',
            'max_memory': 'Unknown',
            'memory_slots': 'Unknown'
        }

        if platform.system() == 'Linux':
            # 尝试使用dmidecode获取主板信息（不使用sudo）
            try:
                output = subprocess.run(['dmidecode', '-t', 'baseboard'], capture_output=True, text=True)
                if output.returncode == 0:
                    mobo_info = analyze_dmidecode_baseboard(output.stdout, mobo_info)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

            # 尝试使用lshw命令获取主板信息（不使用sudo）
            try:
                output = subprocess.run(['lshw', '-class', 'bus'], capture_output=True, text=True)
                if output.returncode == 0:
                    mobo_info = analyze_lshw_baseboard(output.stdout, mobo_info)
            except (subprocess.SubprocessError, FileNotFoundError):
                # 如果lshw不可用，使用备用方法
                mobo_info = fetch_fallback_mobo_info(mobo_info)

            # 尝试从/sys/class/dmi获取主板信息
            try:
                dmi_path = '/sys/class/dmi/id'
                if os.path.exists(dmi_path):
                    board_vendor_file = os.path.join(dmi_path, 'board_vendor')
                    board_name_file = os.path.join(dmi_path, 'board_name')
                    board_serial_file = os.path.join(dmi_path, 'board_serial')

                    if os.path.exists(board_vendor_file):
                        with open(board_vendor_file, 'r') as f:
                            mobo_info['vendor'] = f.read().strip()

                    if os.path.exists(board_name_file):
                        with open(board_name_file, 'r') as f:
                            mobo_info['model'] = f.read().strip()

                    if os.path.exists(board_serial_file):
                        with open(board_serial_file, 'r') as f:
                            mobo_info['serial'] = f.read().strip()
            except Exception:
                pass

            # 尝试获取芯片组信息
            try:
                output = subprocess.run(['lspci', '-nn'], capture_output=True, text=True)
                if output.returncode == 0:
                    chipset_info = analyze_chipset_info(output.stdout)
                    if chipset_info:
                        mobo_info['chipset'] = chipset_info
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                # 获取主板信息
                output = subprocess.run(['system_profiler', 'SPHardwareDataType'], capture_output=True, text=True)
                if output.returncode == 0:
                    mobo_info = analyze_macos_baseboard(output.stdout, mobo_info)
            except subprocess.SubprocessError:
                pass

            # 获取芯片组信息
            try:
                output = subprocess.run(['system_profiler', 'SPPCIDataType'], capture_output=True, text=True)
                if output.returncode == 0:
                    chipset_info = analyze_macos_chipset(output.stdout)
                    if chipset_info:
                        mobo_info['chipset'] = chipset_info
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                # 获取主板信息
                output = subprocess.run(['wmic', 'baseboard', 'get', 'Manufacturer,Product,SerialNumber,Version'], capture_output=True, text=True)
                if output.returncode == 0:
                    mobo_info = analyze_windows_baseboard(output.stdout, mobo_info)
            except subprocess.SubprocessError:
                pass

            # 获取芯片组信息
            try:
                output = subprocess.run(['wmic', 'path', 'Win32_PnPEntity', 'where', '"DeviceID like \'%PCI\\\\VEN%&DEV%\'"', 'get', 'Name,DeviceID'], capture_output=True, text=True)
                if output.returncode == 0:
                    chipset_info = analyze_windows_chipset(output.stdout)
                    if chipset_info:
                        mobo_info['chipset'] = chipset_info
            except subprocess.SubprocessError:
                pass

        return mobo_info

    except Exception as e:
        logger.error(f'获取主板详细信息失败: {e}')
        return {
            'vendor': 'Unknown',
            'model': 'Unknown',
            'serial': 'Unknown',
            'chipset': 'Unknown',
            'form_factor': 'Unknown',
            'max_memory': 'Unknown',
            'memory_slots': 'Unknown'
        }
def analyze_dmidecode_baseboard(output, mobo_info):
    """
    解析dmidecode主板输出

    参数:
        output: dmidecode输出
        mobo_info: 主板信息字典

    返回:
        更新后的主板信息字典
    """
    try:
        lines = output.split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('Manufacturer:'):
                mobo_info['vendor'] = line.split(':', 1)[1].strip()
            elif line.startswith('Product Name:'):
                mobo_info['model'] = line.split(':', 1)[1].strip()
            elif line.startswith('Serial Number:'):
                mobo_info['serial'] = line.split(':', 1)[1].strip()
            elif line.startswith('Version:'):
                mobo_info['form_factor'] = line.split(':', 1)[1].strip()
            elif line.startswith('Number Of Memory Slots:'):
                mobo_info['memory_slots'] = line.split(':', 1)[1].strip()

        return mobo_info

    except Exception as e:
        logger.error(f'解析dmidecode主板输出失败: {e}')
        return mobo_info
def analyze_lshw_baseboard(output, mobo_info):
    """
    解析lshw主板输出

    参数:
        output: lshw输出
        mobo_info: 主板信息字典

    返回:
        更新后的主板信息字典
    """
    try:
        lines = output.split('\n')

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('vendor:'):
                mobo_info['vendor'] = stripped_line.split(':', 1)[1].strip()
            elif stripped_line.startswith('product:'):
                mobo_info['model'] = stripped_line.split(':', 1)[1].strip()
            elif stripped_line.startswith('serial:'):
                mobo_info['serial'] = stripped_line.split(':', 1)[1].strip()
            elif stripped_line.startswith('version:'):
                mobo_info['form_factor'] = stripped_line.split(':', 1)[1].strip()

        return mobo_info

    except Exception as e:
        logger.error(f'解析lshw主板输出失败: {e}')
        return mobo_info
def analyze_macos_baseboard(output, mobo_info):
    """
    解析macOS主板输出

    参数:
        output: system_profiler输出
        mobo_info: 主板信息字典

    返回:
        更新后的主板信息字典
    """
    try:
        lines = output.split('\n')

        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('Model Identifier:'):
                mobo_info['model'] = stripped_line.split(':', 1)[1].strip()
            elif stripped_line.startswith('Serial Number (system):'):
                mobo_info['serial'] = stripped_line.split(':', 1)[1].strip()

        mobo_info['vendor'] = 'Apple'

        return mobo_info

    except Exception as e:
        logger.error(f'解析macOS主板输出失败: {e}')
        # 即使在异常情况下，对于macOS系统也应该设置vendor为Apple
        mobo_info['vendor'] = 'Apple'
        return mobo_info
def analyze_windows_baseboard(output, mobo_info):
    """
    解析Windows主板输出

    参数:
        output: wmic输出
        mobo_info: 主板信息字典

    返回:
        更新后的主板信息字典
    """
    try:
        lines = output.strip().split('\n')[1:]  # 跳过标题行

        if lines:
            line = lines[0].strip()

            # 尝试制表符分隔
            if '\t' in line:
                parts = line.split('\t')
            else:
                # 处理多空格分隔的格式
                # 使用正则表达式按多个连续空格分割，但要保留完整的字段
                # 先按4个或更多空格分割（字段间分隔符）
                parts = re.split(r' {4,}', line)
                # 如果分割结果不合理，尝试按3个空格分割
                if len(parts) < 2:
                    parts = re.split(r' {3,}', line)
                # 如果还是不合理，尝试按2个空格分割
                if len(parts) < 2:
                    parts = re.split(r' {2,}', line)

                # 清理各部分
                parts = [part.strip() for part in parts if part.strip()]

            # 确保有足够的部分
            if len(parts) >= 4:
                mobo_info['vendor'] = parts[0].strip()
                mobo_info['model'] = parts[1].strip()
                mobo_info['serial'] = parts[2].strip()
                mobo_info['form_factor'] = parts[3].strip()
            elif len(parts) >= 3:
                # 如果只有3个部分
                mobo_info['vendor'] = parts[0].strip()
                mobo_info['model'] = parts[1].strip()
                mobo_info['serial'] = parts[2].strip()
                mobo_info['form_factor'] = 'Unknown'
            elif len(parts) >= 2:
                # 如果只有2个部分
                mobo_info['vendor'] = parts[0].strip()
                mobo_info['model'] = parts[1].strip()
                mobo_info['serial'] = 'Unknown'
                mobo_info['form_factor'] = 'Unknown'

        return mobo_info

    except Exception as e:
        logger.error(f'解析Windows主板输出失败: {e}')
        return mobo_info
def analyze_chipset_info(output):
    """
    解析芯片组信息

    参数:
        output: lspci输出

    返回:
        芯片组信息字符串
    """
    try:
        lines = output.split('\n')

        for line in lines:
            if 'Host bridge' in line or 'PCI bridge' in line:
                colon_index = line.find(':')
                if colon_index != -1:
                    chipset = line[colon_index + 1:].strip()
                    if chipset:
                        return chipset

        return 'Unknown'

    except Exception as e:
        logger.error(f'解析芯片组信息失败: {e}')
        return 'Unknown'
def analyze_macos_chipset(output):
    """
    解析macOS芯片组信息

    参数:
        output: system_profiler输出

    返回:
        芯片组信息字符串
    """
    try:
        lines = output.split('\n')

        for line in lines:
            if 'Bridge' in line or 'Chipset' in line:
                return line.strip()

        return 'Unknown'

    except Exception as e:
        logger.error(f'解析macOS芯片组信息失败: {e}')
        return 'Unknown'
def analyze_windows_chipset(output):
    """
    解析Windows芯片组信息

    参数:
        output: wmic输出

    返回:
        芯片组信息字符串
    """
    try:
        lines = output.split('\n')

        for line in lines:
            if 'Host bridge' in line or 'PCI bridge' in line:
                return line.strip()

        return 'Unknown'

    except Exception as e:
        logger.error(f'解析Windows芯片组信息失败: {e}')
        return 'Unknown'
def fetch_mobo_extended_info():
    """
    获取主板扩展信息

    返回:
        主板扩展信息字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                output = subprocess.run(['dmidecode', '-t', 'baseboard'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.split('\n')
                    extended_info = []
                    for line in lines:
                        stripped_line = line.strip()
                        if stripped_line.startswith('Asset Tag:') or \
                           stripped_line.startswith('Location In Chassis:') or \
                           stripped_line.startswith('Chassis Handle:') or \
                           stripped_line.startswith('Type:') or \
                           stripped_line.startswith('Contained Object Handles:'):
                            extended_info.append(stripped_line)
                    return '\n'.join(extended_info[:10])
            except (subprocess.SubprocessError, FileNotFoundError):
                pass

        return None

    except Exception as e:
        logger.error(f'获取主板扩展信息失败: {e}')
        return None
