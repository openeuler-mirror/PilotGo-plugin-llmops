import logging
import os
import platform
import re
import subprocess

from .utils import (

    check_nginx_installation, get_nginx_version, get_nginx_compile_info,
    get_kernel_compatibility, get_nginx_modules, get_nginx_process_info,
    get_nginx_config_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_version')

def fetch_nginx_base_version():
    """
    获取Nginx版本、编译参数、内核适配信息的MCP工具

    返回:
        格式化的Nginx基础信息字符串，包含：
        - Nginx版本信息
        - 编译参数和配置
        - 内核适配信息
        - 模块信息
        - 配置信息
    """
    try:
        output = []
        output.append('=== Nginx基础版本信息 ===')

        # 检查Nginx是否安装
        nginx_info = check_nginx_installation()
        if not nginx_info['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_info['suggestion']}")
            output.append('======================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")
        output.append(f"安装路径: {nginx_info['path']}")

        # 获取版本信息
        ver_data = get_nginx_version()
        output.append(f"\n=== 版本信息 ===")
        output.append(f"主版本: {ver_data['main_version']}")
        output.append(f"详细版本: {ver_data['full_version']}")

        # 获取编译参数
        build_info = get_nginx_compile_info()
        output.append(f"\n=== 编译参数 ===")
        output.append(f"编译器: {build_info['compiler']}")
        output.append(f"编译时间: {build_info['compile_time']}")

        if build_info['configure_args']:
            output.append(f"配置参数:")
            args = build_info['configure_args'].split()
            for i, arg in enumerate(args):
                if arg.startswith('--'):
                    output.append(f"  {arg}")
                else:
                    if i > 0 and not args[i-1].startswith('--'):
                        continue
                    output.append(f"  {arg}")

        # 获取内核适配信息
        kern_info = get_kernel_compatibility()
        output.append(f"\n=== 内核适配信息 ===")
        output.append(f"当前内核版本: {kern_info['current_kernel']}")
        output.append(f"系统架构: {kern_info['architecture']}")
        output.append(f"Nginx内核兼容性: {kern_info['compatibility']}")

        if kern_info['optimization_features']:
            output.append(f"内核优化特性:")
            for feature in kern_info['optimization_features']:
                output.append(f"  - {feature}")

        # 获取模块信息
        mod_info = get_nginx_modules()
        output.append(f"\n=== 模块信息 ===")
        output.append(f"内置模块数量: {mod_info['builtin_modules_count']}")
        output.append(f"动态模块数量: {mod_info['dynamic_modules_count']}")

        if mod_info['builtin_modules']:
            output.append(f"主要内置模块:")
            for module in mod_info['builtin_modules'][:10]:
                output.append(f"  - {module}")
            if len(mod_info['builtin_modules']) > 10:
                output.append(f"  ... 还有 {len(mod_info['builtin_modules']) - 10} 个模块 ...")

        # 获取配置信息
        cfg_state = get_nginx_config_info()
        output.append(f"\n=== 配置信息 ===")
        output.append(f"主配置文件: {cfg_state['config_file']}")
        output.append(f"配置测试: {cfg_state['config_test']}")

        # 仅保留基本进程状态
        proc_info = get_nginx_process_info()
        output.append(f"\n=== 服务状态 ===")
        output.append(f"运行状态: {proc_info['status']}")

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx基础版本信息失败: {e}')
        return f'获取Nginx基础版本信息失败: {e}'

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_base_version",
    "function": fetch_nginx_base_version,
    "description": "获取Nginx版本、编译参数、内核适配和模块信息的MCP工具",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
