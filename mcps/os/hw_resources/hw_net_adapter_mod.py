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
