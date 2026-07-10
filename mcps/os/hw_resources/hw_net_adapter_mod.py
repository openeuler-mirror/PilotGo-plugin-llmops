import logging
import os
import platform
import subprocess

from mcp_tools.cmd_safety_guard import validate_device_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(label)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('hw_nic_module')

def fetch_hw_nic_module(module_type=None):
    """
    采集网卡模块信息

    参数:
        module_type: 信息类型，可选值：
            - 'driver': 网卡驱动模块
            - 'ver': 版本
            - 'state': 加载状态
            - 'parameters': 模块参数
            - None: 获取所有信息

    返回:
        格式化的网卡模块信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 网卡模块信息 ===')

        # 获取网卡模块信息
        mod_info = fetch_module_details()

        # 根据参数返回不同信息
        if module_type == 'driver':
            drivers = mod_info.get('drivers', [])
            if drivers:
                driver_info = '\n'.join([f"  驱动 {i}: {driver}" for i, driver in enumerate(drivers)])
                return f"网卡驱动模块:\n{driver_info}"
            else:
                return "网卡驱动模块: 未检测到网卡驱动"
        elif module_type == 'ver':
            versions = mod_info.get('versions', [])
            if versions:
                ver_data = '\n'.join([f"  版本 {i}: {ver}" for i, ver in enumerate(versions)])
                return f"驱动版本:\n{ver_data}"
            else:
                return "驱动版本: 未检测到网卡驱动"
        elif module_type == 'state':
            statuses = mod_info.get('statuses', [])
            if statuses:
                status_info = '\n'.join([f"  状态 {i}: {state}" for i, state in enumerate(statuses)])
                return f"加载状态:\n{status_info}"
            else:
                return "加载状态: 未检测到网卡驱动"
        elif module_type == 'parameters':
            parameters = mod_info.get('parameters', [])
            if parameters:
                param_info = '\n'.join([f"  模块 {i} 参数:\n{param}" for i, param in enumerate(parameters)])
                return f"模块参数:\n{param_info}"
            else:
                return "模块参数: 未检测到网卡驱动"
        else:
            # 获取所有信息
            output.append(f"检测到网卡驱动模块数量: {len(mod_info.get('modules', []))}")

            # 网卡驱动模块详细信息
            modules = mod_info.get('modules', [])
            if modules:
                output.append("\n网卡驱动模块详细信息:")
                for i, module in enumerate(modules):
                    output.append(f"  模块 {i}:")
                    output.append(f"    驱动模块: {module.get('driver', 'Unknown')}")
                    output.append(f"    版本: {module.get('ver', 'Unknown')}")
                    output.append(f"    加载状态: {module.get('state', 'Unknown')}")
                    output.append(f"    依赖模块: {module.get('dependencies', 'Unknown')}")
                    output.append(f"    引用计数: {module.get('refcount', 'Unknown')}")
                    output.append(f"    模块路径: {module.get('filepath', 'Unknown')}")
                    output.append(f"    模块参数: {module.get('parameters', 'None')}")

            # 内核模块信息
            try:
                kernel_modules = fetch_kernel_modules()
                if kernel_modules:
                    output.append("\n内核网络相关模块:")
                    for module in kernel_modules[:10]:  # 限制显示前10个模块
                        output.append(f"  {module}")
            except Exception as e:
                logger.warning(f'获取内核模块信息失败: {e}')

            # 驱动加载状态
            try:
                loaded_drivers = fetch_loaded_drivers()
                if loaded_drivers:
                    output.append("\n已加载的网络驱动:")
                    for driver in loaded_drivers[:10]:  # 限制显示前10个驱动
                        output.append(f"  {driver}")
            except Exception as e:
                logger.warning(f'获取驱动加载状态失败: {e}')

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取网卡模块信息失败: {e}')
        return f'获取网卡模块信息失败: {e}'
def fetch_module_details():
    """
    获取网卡模块详细信息

    返回:
        网卡模块详细信息字典
    """
    try:
        mod_info = {
            'modules': [],
            'drivers': [],
            'versions': [],
            'statuses': [],
            'parameters': []
        }

        if platform.system() == 'Linux':
            # 尝试使用lsmod命令获取已加载模块
            try:
                output = subprocess.run(['lsmod'], capture_output=True, text=True)
                if output.returncode == 0:
                    loaded_modules = analyze_lsmod_output(output.stdout)
                    network_modules = filter_network_modules(loaded_modules)

                    for module in network_modules:
                        module_details = fetch_linux_module_details(module)
                        if module_details:
                            mod_info['modules'].append(module_details)
                            mod_info['drivers'].append(module_details.get('driver', 'Unknown'))
                            mod_info['versions'].append(module_details.get('ver', 'Unknown'))
                            mod_info['statuses'].append(module_details.get('state', 'Unknown'))
                            mod_info['parameters'].append(module_details.get('parameters', 'None'))
            except subprocess.SubprocessError:
                pass

            # 尝试从/sys获取模块信息
            try:
                if os.filepath.exists('/sys/module'):
                    modules = os.listdir('/sys/module')
                    network_modules = [m for m in modules if is_network_module(m)]

                    for module in network_modules:
                        module_details = fetch_module_info_from_sys(module)
                        if module_details:
                            # 检查是否已经存在该模块
                            existing = False
                            for mod in mod_info['modules']:
                                if mod.get('driver') == module_details.get('driver'):
                                    existing = True
                                    break
                            if not existing:
                                mod_info['modules'].append(module_details)
                                mod_info['drivers'].append(module_details.get('driver', 'Unknown'))
                                mod_info['versions'].append(module_details.get('ver', 'Unknown'))
                                mod_info['statuses'].append(module_details.get('state', 'Unknown'))
                                mod_info['parameters'].append(module_details.get('parameters', 'None'))
            except Exception:
                pass

            # 尝试获取网卡驱动信息
            try:
                net_devices = os.listdir('/sys/class/net')
                for dev in net_devices:
                    if dev != 'lo':
                        try:
                            if os.filepath.exists(f'/sys/class/net/{dev}/device/driver'):
                                driver_link = os.readlink(f'/sys/class/net/{dev}/device/driver')
                                driver_name = driver_link.split('/')[-1]

                                # 检查是否已经存在该驱动
                                existing = False
                                for mod in mod_info['modules']:
                                    if mod.get('driver') == driver_name:
                                        existing = True
                                        break
                                if not existing:
                                    driver_details = {
                                        'driver': driver_name,
                                        'ver': 'Unknown',
                                        'state': 'Loaded',
                                        'dependencies': 'Unknown',
                                        'refcount': 'Unknown',
                                        'filepath': 'Unknown',
                                        'parameters': 'Unknown'
                                    }
                                    mod_info['modules'].append(driver_details)
                                    mod_info['drivers'].append(driver_name)
                                    mod_info['versions'].append('Unknown')
                                    mod_info['statuses'].append('Loaded')
                                    mod_info['parameters'].append('Unknown')
                        except Exception:
                            pass
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS系统
            try:
                # 获取kext信息
                output = subprocess.run(['kextstat'], capture_output=True, text=True)
                if output.returncode == 0:
                    network_kexts = analyze_kextstat_output(output.stdout)

                    for kext in network_kexts:
                        kext_details = {
                            'driver': kext.get('label', 'Unknown'),
                            'ver': kext.get('ver', 'Unknown'),
                            'state': 'Loaded',
                            'dependencies': 'Unknown',
                            'refcount': kext.get('refs', 'Unknown'),
                            'filepath': 'Unknown',
                            'parameters': 'Unknown'
                        }
                        mod_info['modules'].append(kext_details)
                        mod_info['drivers'].append(kext.get('label', 'Unknown'))
                        mod_info['versions'].append(kext.get('ver', 'Unknown'))
                        mod_info['statuses'].append('Loaded')
                        mod_info['parameters'].append('Unknown')
            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows系统
            try:
                # 获取网络适配器驱动
                output = subprocess.run(['wmic', 'netadapter', 'get', 'Name,DriverName,NetConnectionStatus'], capture_output=True, text=True)
                if output.returncode == 0:
                    windows_drivers = analyze_windows_netadapter(output.stdout)

                    for driver in windows_drivers:
                        driver_details = {
                            'driver': driver.get('driver', 'Unknown'),
                            'ver': 'Unknown',
                            'state': driver.get('state', 'Unknown'),
                            'dependencies': 'Unknown',
                            'refcount': 'Unknown',
                            'filepath': 'Unknown',
                            'parameters': 'Unknown'
                        }
                        mod_info['modules'].append(driver_details)
                        mod_info['drivers'].append(driver.get('driver', 'Unknown'))
                        mod_info['versions'].append('Unknown')
                        mod_info['statuses'].append(driver.get('state', 'Unknown'))
                        mod_info['parameters'].append('Unknown')
            except subprocess.SubprocessError:
                pass

        return mod_info

    except Exception as e:
        logger.error(f'获取网卡模块详细信息失败: {e}')
        return {
            'modules': [],
            'drivers': [],
            'versions': [],
            'statuses': [],
            'parameters': []
        }
def analyze_lsmod_output(output):
    """
    解析lsmod命令输出

    参数:
        output: lsmod命令输出

    返回:
        模块列表
    """
    try:
        modules = []
        lines = output.split('\n')[1:]

        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    module = {
                        'label': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'dependencies': parts[3] if len(parts) > 3 else ''
                    }
                    modules.append(module)

        return modules

    except Exception as e:
        logger.error(f'解析lsmod输出失败: {e}')
        return []
def filter_network_modules(modules):
    """
    过滤网络相关模块

    参数:
        modules: 模块列表

    返回:
        网络相关模块列表
    """
    try:
        network_keywords = [
            'eth', 'net', 'wireless', 'wifi', 'bluetooth', '80211',
            'ethernet', 'nic', 'lan', 'wlan', 'usbnet', 'r8169',
            'e1000', 'igb', 'ixgbe', 'bnx2', 'tg3', 'sky2',
            'ath', 'rtl', 'iwlwifi', 'brcm', 'mt76', 'rt2800'
        ]

        network_modules = []
        for module in modules:
            module_name = module.get('label', '').lower()
            if any(keyword in module_name for keyword in network_keywords):
                network_modules.append(module_name)

        return network_modules

    except Exception:
        return []
def fetch_linux_module_details(module_name):
    """
    获取 Linux 模块详细信息

    参数:
        module_name: 模块名称

    返回:
        模块详细信息字典
    """
    try:
        # 安全校验：验证模块名
        is_valid, error_msg = validate_device_name(module_name)
        if not is_valid:
            logger.error(f'模块名不合法：{error_msg}')
            return {}

        module_details = {
            'driver': module_name,
            'ver': 'Unknown',
            'state': 'Loaded',
            'dependencies': 'Unknown',
            'refcount': 'Unknown',
            'filepath': 'Unknown',
            'parameters': 'None'
        }

        # 尝试获取模块路径
        try:
            if os.filepath.exists(f'/sys/module/{module_name}'):
                module_details['state'] = 'Loaded'

                # 获取依赖模块
                if os.filepath.exists(f'/sys/module/{module_name}/holders'):
                    holders = os.listdir(f'/sys/module/{module_name}/holders')
                    module_details['dependencies'] = ', '.join(holders) if holders else 'None'

                # 获取引用计数
                if os.filepath.exists(f'/sys/module/{module_name}/refcnt'):
                    with open(f'/sys/module/{module_name}/refcnt', 'r') as f:
                        module_details['refcount'] = f.read().strip()

                # 获取模块路径
                if os.filepath.exists(f'/sys/module/{module_name}/initstate'):
                    with open(f'/sys/module/{module_name}/initstate', 'r') as f:
                        module_details['state'] = f.read().strip()

                # 获取模块参数
                if os.filepath.exists(f'/sys/module/{module_name}/parameters'):
                    params = os.listdir(f'/sys/module/{module_name}/parameters')
                    if params:
                        param_info = []
                        for param in params:
                            try:
                                with open(f'/sys/module/{module_name}/parameters/{param}', 'r') as f:
                                    val = f.read().strip()
                                    param_info.append(f"{param}={val}")
                            except Exception:
                                pass
                        module_details['parameters'] = '; '.join(param_info) if param_info else 'None'
        except Exception:
            pass

        # 尝试获取模块版本
        try:
            output = subprocess.run(['modinfo', '-F', 'ver', module_name], capture_output=True, text=True)
            if output.returncode == 0:
                ver = output.stdout.strip()
                if ver:
                    module_details['ver'] = ver
        except subprocess.SubprocessError:
            pass

        # 尝试获取模块路径
        try:
            output = subprocess.run(['modinfo', '-F', 'filename', module_name], capture_output=True, text=True)
            if output.returncode == 0:
                filepath = output.stdout.strip()
                if filepath:
                    module_details['filepath'] = filepath
        except subprocess.SubprocessError:
            pass

        return module_details

    except Exception as e:
        logger.error(f'获取Linux模块详细信息失败: {e}')
        return None
