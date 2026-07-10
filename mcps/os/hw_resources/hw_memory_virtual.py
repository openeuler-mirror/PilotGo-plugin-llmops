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
def fetch_virtual_memory_details():
    """
    获取虚拟内存详细信息

    返回:
        虚拟内存详细信息字典
    """
    try:
        vmem_info = {
            'page_size': 'Unknown',
            'address_bits': 'Unknown',
            'virtual_address_space': 'Unknown',
            'physical_address_space': 'Unknown',
            'swap': {},
            'swap_total': 'Unknown',
            'swap_used': 'Unknown',
            'swap_free': 'Unknown'
        }

        if platform.system() == 'Linux':
            # 获取页面大小
            try:
                output = subprocess.run(['getconf', 'PAGESIZE'], capture_output=True, text=True)
                if output.returncode == 0:
                    page_size = int(output.stdout.strip())
                    # 避免浮点数溢出，使用更安全的格式化
                    if page_size >= 1024:
                        kb_size = page_size // 1024
                        remainder = page_size % 1024
                        if remainder == 0:
                            vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.00 KB)"
                        else:
                            vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.{remainder//102:02d} KB)"
                    else:
                        vmem_info['page_size'] = f"{page_size} bytes"
            except subprocess.SubprocessError:
                pass

            # 获取地址位数
            try:
                output = subprocess.run(['getconf', 'LONG_BIT'], capture_output=True, text=True)
                if output.returncode == 0:
                    vmem_info['address_bits'] = output.stdout.strip() + ' bits'
            except subprocess.SubprocessError:
                pass

            # 获取虚拟地址空间大小
            try:
                output = subprocess.run(['getconf', 'VIRTUAL_ADDRESS_BITS'], capture_output=True, text=True)
                if output.returncode == 0:
                    vmem_info['virtual_address_space'] = output.stdout.strip() + ' bits'
            except subprocess.SubprocessError:
                pass

            # 获取物理地址空间大小
            try:
                output = subprocess.run(['getconf', 'PHYSICAL_ADDRESS_BITS'], capture_output=True, text=True)
                if output.returncode == 0:
                    vmem_info['physical_address_space'] = output.stdout.strip() + ' bits'
            except subprocess.SubprocessError:
                pass

            # 获取交换分区信息
            try:
                # 首先尝试读取/proc/swaps
                proc_swaps_info = {}
                try:
                    with open('/proc/swaps', 'r') as f:
                        body = f.read()
                        proc_swaps_info = analyze_proc_swaps_info(body)
                except FileNotFoundError:
                    pass

                # 然后尝试使用swapon命令
                swap_info = {}
                try:
                    output = subprocess.run(['swapon', '--show'], capture_output=True, text=True)
                    if output.returncode == 0:
                        swap_info = analyze_swap_info(output.stdout)
                except subprocess.SubprocessError:
                    pass

                # 合并两种来源的信息
                vmem_info['swap'] = swap_info

                # 计算总交换空间（优先使用/proc/swaps数据）
                if proc_swaps_info and 'SwapTotal' in proc_swaps_info:
                    total_swap = proc_swaps_info['SwapTotal']
                    free_swap = proc_swaps_info.get('SwapFree', 0)
                    used_swap = total_swap - free_swap

                    vmem_info['swap_total'] = f"{total_swap} KB ({total_swap/1024/1024:.2f} GB)" if total_swap > 0 else "0 KB"
                    vmem_info['swap_used'] = f"{used_swap} KB ({used_swap/1024/1024:.2f} GB)" if used_swap > 0 else "0 KB"
                    vmem_info['swap_free'] = f"{free_swap} KB ({free_swap/1024/1024:.2f} GB)" if free_swap > 0 else "0 KB"
                elif swap_info:
                    # 使用swapon数据
                    total_swap = 0
                    used_swap = 0
                    for swap_dev in swap_info.values():
                        # 解析SIZE字段（如8G）
                        size_str = swap_dev.get('size', '0')
                        used_str = swap_dev.get('used', '0')

                        # 简单的单位转换（G->KB）
                        def analyze_size(size_str):
                            if size_str.endswith('G'):
                                return int(float(size_str[:-1]) * 1024 * 1024)
                            elif size_str.endswith('M'):
                                return int(float(size_str[:-1]) * 1024)
                            elif size_str.endswith('K'):
                                return int(size_str[:-1])
                            else:
                                return int(size_str)

                        total_swap += analyze_size(size_str)
                        used_swap += analyze_size(used_str)

                    vmem_info['swap_total'] = f"{total_swap} KB ({total_swap/1024/1024:.2f} GB)" if total_swap > 0 else "0 KB"
                    vmem_info['swap_used'] = f"{used_swap} KB ({used_swap/1024/1024:.2f} GB)" if used_swap > 0 else "0 KB"
                    vmem_info['swap_free'] = f"{total_swap - used_swap} KB ({(total_swap - used_swap)/1024/1024:.2f} GB)" if total_swap > used_swap else "0 KB"
            except Exception:
                pass

        elif platform.system() == 'Darwin':
            # macOS下的实现
            try:
                # 首先尝试使用vm_stat获取页面大小
                output = subprocess.run(['vm_stat'], capture_output=True, text=True)
                if output.returncode == 0:
                    # 解析vm_stat输出
                    for line in output.stdout.split('\n'):
                        if 'page size' in line.lower():
                            # 提取页面大小数值
                            match = re.search(r'page size = (\d+) bytes', line)
                            if match:
                                page_size = int(match.group(1))
                                if page_size >= 1024:
                                    kb_size = page_size // 1024
                                    remainder = page_size % 1024
                                    if remainder == 0:
                                        vmem_info['page_size'] = f"{page_size} bytes ({kb_size} KB)"
                                    else:
                                        vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.{remainder//102:02d} KB)"
                                else:
                                    vmem_info['page_size'] = f"{page_size} bytes"
                                break

                # 如果vm_stat失败，尝试使用pagesize命令
                if vmem_info['page_size'] == 'Unknown':
                    output = subprocess.run(['pagesize'], capture_output=True, text=True)
                    if output.returncode == 0:
                        page_size = int(output.stdout.strip())
                        if page_size >= 1024:
                            kb_size = page_size // 1024
                            remainder = page_size % 1024
                            if remainder == 0:
                                vmem_info['page_size'] = f"{page_size} bytes ({kb_size} KB)"
                            else:
                                vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.{remainder//102:02d} KB)"
                        else:
                            vmem_info['page_size'] = f"{page_size} bytes"

                # 获取地址位数
                output = subprocess.run(['sysctl', '-n', 'hw.cpu64bit_capable'], capture_output=True, text=True)
                if output.returncode == 0:
                    if output.stdout.strip() == '1':
                        vmem_info['address_bits'] = '64 bits'
                    else:
                        vmem_info['address_bits'] = '32 bits'

            except subprocess.SubprocessError:
                pass

        elif platform.system() == 'Windows':
            # Windows下的实现
            try:
                # 获取页面大小
                output = subprocess.run(['wmic', 'os', 'get', 'PageSize'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.strip().split('\n')[1:]
                    if lines:
                        page_size = int(lines[0].strip())
                        if page_size >= 1024:
                            kb_size = page_size // 1024
                            remainder = page_size % 1024
                            if remainder == 0:
                                vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.00 KB)"
                            else:
                                vmem_info['page_size'] = f"{page_size} bytes ({kb_size}.{remainder//102:02d} KB)"
                        else:
                            vmem_info['page_size'] = f"{page_size} bytes"

                # 获取地址位数
                output = subprocess.run(['wmic', 'os', 'get', 'OSArchitecture'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.strip().split('\n')[1:]
                    if lines:
                        arch = lines[0].strip()
                        if '64' in arch:
                            vmem_info['address_bits'] = '64 bits'
                            vmem_info['virtual_address_space'] = '128 TB'
                            vmem_info['physical_address_space'] = '128 GB'
                        else:
                            vmem_info['address_bits'] = '32 bits'
                            vmem_info['virtual_address_space'] = '4 GB'
                            vmem_info['physical_address_space'] = '4 GB'

                # 获取交换分区信息
                output = subprocess.run(['wmic', 'pagefile', 'get', 'Name,Size'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.strip().split('\n')
                    if len(lines) > 1:
                        # 解析表头和数据行
                        header = lines[0].strip()
                        if len(lines) > 1:
                            data_line = lines[1].strip()
                            # 简单按空格分割（实际应该更精确地按列位置解析）
                            parts = data_line.split()
                            if len(parts) >= 2:
                                label = parts[0]
                                try:
                                    size_mb = int(parts[1])
                                    vmem_info['swap'] = {
                                        label: {
                                            'size_kb': size_mb * 1024,
                                            'used_kb': 0  # Windows不提供详细使用信息
                                        }
                                    }
                                except ValueError:
                                    pass
            except subprocess.SubprocessError:
                pass

        return vmem_info

    except Exception as e:
        logger.error(f'获取虚拟内存详细信息失败: {e}')
        logger.error(f'异常类型: {type(e).__name__}')
        logger.error(f'异常详情: {repr(e)}')
        logger.error(f'调用栈: {traceback.format_exc()}')
        return {
            'page_size': 'Unknown',
            'address_bits': 'Unknown',
            'virtual_address_space': 'Unknown',
            'physical_address_space': 'Unknown',
            'swap': {},
            'swap_total': 'Unknown',
            'swap_used': 'Unknown',
            'swap_free': 'Unknown'
        }
def analyze_swap_info(output):
    """
    解析交换分区信息

    参数:
        output: swapon输出

    返回:
        交换分区信息字典
    """
    try:
        swap_info = {}
        lines = output.strip().split('\n')

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 5:
                swap_device = parts[0]
                swap_type = parts[1]
                swap_size = parts[2]
                swap_used = parts[3]
                swap_priority = parts[4]

                swap_info[swap_device] = {
                    'type': swap_type,
                    'size': swap_size,
                    'used': swap_used,
                    'priority': swap_priority
                }

        return swap_info

    except Exception as e:
        logger.error(f'解析交换分区信息失败: {e}')
        return {}
def analyze_macos_swap_info(output):
    """
    解析macOS交换分区信息

    参数:
        output: sysctl输出

    返回:
        交换分区信息字典
    """
    try:
        swap_info = {}

        # macOS的交换分区信息格式: "total = 1024.00M  used = 512.00M  free = 512.00M  (encrypted)"
        parts = output.split()
        if len(parts) >= 6:
            total = parts[2]
            used = parts[5]
            free = parts[8]

            swap_info['vm_swapfile'] = {
                'type': 'file',
                'size': total,
                'used': used,
                'priority': 'N/A'
            }

        return swap_info

    except Exception as e:
        logger.error(f'解析macOS交换分区信息失败: {e}')
        return {}
def analyze_windows_swap_info(output):
    """
    解析Windows交换分区信息

    参数:
        output: wmic输出

    返回:
        交换分区信息字典
    """
    try:
        swap_info = {}
        lines = output.strip().split('\n')[1:]

        for line in lines:
            if line.strip():
                parts = [part.strip() for part in line.split() if part.strip()]
                if len(parts) >= 2:
                    swap_file = parts[0]
                    swap_size = parts[1]

                    swap_info[swap_file] = {
                        'type': 'file',
                        'size': f"{int(swap_size) / 1024 / 1024:.2f} GB",
                        'used': 'Unknown',
                        'priority': 'N/A'
                    }

        return swap_info

    except Exception as e:
        logger.error(f'解析Windows交换分区信息失败: {e}')
        return {}
def render_swap_info(swap_info):
    """
    格式化交换分区信息

    参数:
        swap_info: 交换分区信息字典

    返回:
        格式化的交换分区信息字符串
    """
    try:
        output = []
        for device, info in swap_info.items():
            output.append(f"  设备: {device}")
            output.append(f"    类型: {info.get('type', 'Unknown')}")
            output.append(f"    大小: {info.get('size', 'Unknown')}")
            output.append(f"    已用: {info.get('used', 'Unknown')}")
            output.append(f"    优先级: {info.get('priority', 'Unknown')}")
        return '\n'.join(output)
    except Exception as e:
        logger.error(f'格式化交换分区信息失败: {e}')
        return "格式化交换分区信息失败"
def fetch_swap_usage():
    """
    获取交换分区使用情况

    返回:
        交换分区使用情况字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            key = parts[0].rstrip(':')
                            val = int(parts[1])
                            meminfo[key] = val

                    swap_total = meminfo.get('SwapTotal', 0)
                    swap_free = meminfo.get('SwapFree', 0)
                    swap_used = swap_total - swap_free

                    total_gb = swap_total / 1024 / 1024
                    used_gb = swap_used / 1024 / 1024
                    free_gb = swap_free / 1024 / 1024
                    usage_percent = (swap_used / swap_total) * 100 if swap_total > 0 else 0

                    return '\n'.join([f"交换分区已用: {used_gb:.2f} GB ({usage_percent:.1f}%)", f"交换分区空闲: {free_gb:.2f} GB"])
            except Exception:
                pass

        return None

    except Exception as e:
        logger.error(f'获取交换分区使用情况失败: {e}')
        return None
def fetch_virtual_memory_management():
    """
    获取虚拟内存管理信息

    返回:
        虚拟内存管理信息字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                output = subprocess.run(['vmstat', '-s'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.split('\n')
                    relevant_lines = [line.strip() for line in lines[:10]]
                    return '\n'.join(relevant_lines)
            except subprocess.SubprocessError:
                pass

        return None

    except Exception as e:
        logger.error(f'获取虚拟内存管理信息失败: {e}')
        return None
def fetch_memory_mapping_info():
    """
    获取内存映射信息

    返回:
        内存映射信息字符串
    """
    try:
        if platform.system() == 'Linux':
            try:
                # 获取当前进程的内存映射
                output = subprocess.run(['cat', '/proc/self/maps'], capture_output=True, text=True)
                if output.returncode == 0:
                    lines = output.stdout.split('\n')
                    mapping_types = {}
                    for line in lines[:20]:
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 5:
                                perms = parts[1]
                                if perms not in mapping_types:
                                    mapping_types[perms] = 0
                                mapping_types[perms] += 1

                    output = []
                    output.append("内存映射类型统计:")
                    for perms, count in mapping_types.items():
                        output.append(f"  {perms}: {count} 个映射")
                    return '\n'.join(output)
            except subprocess.SubprocessError:
                pass

        return None

    except Exception as e:
        logger.error(f'获取内存映射信息失败: {e}')
        return None
