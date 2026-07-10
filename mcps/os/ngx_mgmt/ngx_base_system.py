import logging
import os
import sys

from hardware_resources.hw_cpu_basic import fetch_hw_cpu_basic
from hardware_resources.hw_disk_physical import fetch_hw_disk_physical
from hardware_resources.hw_mem_physical import fetch_hw_mem_physical
from software_applications.app_rpm_list import fetch_app_rpm_list
from system_basics.sys_arch_info import fetch_sys_arch_info
from system_basics.sys_dist_info import fetch_sys_dist_info
from system_basics.sys_kernel_info import fetch_sys_kernel_info
from system_runtime.run_sys_load import fetch_run_sys_load

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_system')

# 导入现有的系统工具
sys.path.append('/home/wbj/soft/kylin-ops-mcp/mcp_tools/mcp_tools')

try:
    logger.info("成功导入系统工具模块")
except ImportError as e:
    logger.error(f"导入系统工具模块失败: {e}")
    # 设置空函数作为备选
    def fetch_sys_dist_info(info_type=None):
        return "系统发行版信息获取模块未找到"
    def fetch_sys_kernel_info(info_type=None):
        return "内核信息获取模块未找到"
    def fetch_sys_arch_info(info_type=None):
        return "系统架构信息获取模块未找到"
    def fetch_hw_cpu_basic(info_type=None):
        return "CPU基础信息获取模块未找到"
    def fetch_hw_mem_physical(mem_type=None):
        return "物理内存信息获取模块未找到"
    def fetch_hw_disk_physical(disk_type=None):
        return "物理磁盘信息获取模块未找到"
    def fetch_run_sys_load():
        return "系统负载信息获取模块未找到"
    def fetch_app_rpm_list(rpm_info=None):
        return "RPM包信息获取模块未找到"

def fetch_nginx_base_system():
    """
    获取系统运行环境信息的MCP工具，整合现有系统工具提供：
    - 操作系统信息
    - 内核版本和配置
    - CPU信息和架构
    - 内存配置和状态
    - 磁盘信息和挂载情况
    - 系统负载状态
    - 已安装软件包信息
    - Nginx运行环境适配性评估

    返回:
        格式化的系统运行环境信息字符串
    """
    try:
        output = []
        output.append('=== Nginx系统运行环境信息 ===')

        # 获取操作系统信息
        output.append('\n=== 操作系统信息 ===')
        dist_info = fetch_sys_dist_info()
        output.append(dist_info)

        # 获取内核信息
        output.append('\n=== 内核信息 ===')
        kern_info = fetch_sys_kernel_info()
        output.append(kern_info)

        # 获取系统架构信息
        output.append('\n=== 系统架构信息 ===')
        arch_info = fetch_sys_arch_info()
        output.append(arch_info)

        # 获取CPU基础信息
        output.append('\n=== CPU基础信息 ===')
        proc_data = fetch_hw_cpu_basic()
        output.append(proc_data)

        # 获取物理内存信息
        output.append('\n=== 物理内存信息 ===')
        mem_data = fetch_hw_mem_physical()
        output.append(mem_data)

        # 获取物理磁盘信息
        output.append('\n=== 物理磁盘信息 ===')
        disk_info = fetch_hw_disk_physical()
        output.append(disk_info)

        # 获取系统负载信息
        output.append('\n=== 系统负载信息 ===')
        load_info = fetch_run_sys_load()
        output.append(load_info)

        # 获取已安装软件包信息（RPM）
        output.append('\n=== 已安装软件包信息 ===')
        rpm_info = fetch_app_rpm_list()
        output.append(rpm_info)

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取系统运行环境信息失败: {e}')
        return f'获取系统运行环境信息失败: {e}'


# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_base_system",
    "function": fetch_nginx_base_system,
    "description": "获取系统运行环境信息，整合现有系统工具提供OS/内核/CPU/内存/磁盘/负载/软件包信息和Nginx适配性评估",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
