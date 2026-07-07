#!/usr/bin/env python3

from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import re
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_global')


def render_global_config_output(config_data: Dict[str, Any]) -> str:
    """
    格式化全局配置输出

    参数:
        config_data: 全局配置数据

    返回:
        格式化后的字符串
    """
    if 'error' in config_data:
        return f"错误: {config_data['error']}\n建议: {config_data.get('suggestion', '')}"

    output = []
    output.append("=" * 60)
    output.append("Nginx全局配置信息")
    output.append("=" * 60)
    output.append(f"配置文件: {config_data['config_file']}")
    output.append(f"配置测试: {config_data['config_test']}")
    output.append("")

    # 全局指令
    if config_data['global_directives']:
        output.append("【全局指令】")
        output.append("-" * 40)
        for directive, info in config_data['global_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【全局指令】")
        output.append("-" * 40)
        output.append("未找到全局指令")
        output.append("")

    # events指令
    if config_data['events_directives']:
        output.append("【Events模块指令】")
        output.append("-" * 40)
        for directive, info in config_data['events_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【Events模块指令】")
        output.append("-" * 40)
        output.append("未找到Events模块指令")
        output.append("")

    # http指令
    if config_data['http_directives']:
        output.append("【HTTP模块指令】")
        output.append("-" * 40)
        for directive, info in config_data['http_directives'].items():
            output.append(f"{directive}: {info['value']}")
            output.append(f"  说明: {info['description']}")
            output.append("")
    else:
        output.append("【HTTP模块指令】")
        output.append("-" * 40)
        output.append("未找到HTTP模块指令")
        output.append("")

    # include指令
    if config_data['includes']:
        output.append("【Include指令】")
        output.append("-" * 40)
        for include_path in config_data['includes']:
            output.append(f"include {include_path}")
        output.append("")

    # 统计信息
    summary = config_data['summary']
    output.append("【统计信息】")
    output.append("-" * 40)
    output.append(f"全局指令数量: {summary['total_global_directives']}")
    output.append(f"Events指令数量: {summary['total_events_directives']}")
    output.append(f"HTTP指令数量: {summary['total_http_directives']}")
    output.append(f"Include指令数量: {summary['total_includes']}")

    return "\n".join(output)
