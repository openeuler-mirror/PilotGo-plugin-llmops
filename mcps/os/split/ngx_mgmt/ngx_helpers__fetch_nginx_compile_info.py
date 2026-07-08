#!/usr/bin/env python3

import logging
import os
import platform
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_utils')


def fetch_nginx_compile_info():
    """
    获取Nginx编译信息

    返回:
        dict: 包含编译器、编译时间和配置参数的字典
    """
    try:
        # 获取编译参数
        output = subprocess.run(['nginx', '-V'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        build_info = {
            'compiler': 'Unknown',
            'compile_time': 'Unknown',
            'build_opts': ''
        }

        if output.returncode == 0:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 解析编译器信息
            compiler_match = re.search(r'built by ([^\n]+)', output)  # NOSONAR
            if compiler_match:
                build_info['compiler'] = compiler_match.group(1).strip()

            # 解析编译时间
            time_match = re.search(r'built on ([^\n]+)', output)  # NOSONAR
            if time_match:
                build_info['compile_time'] = time_match.group(1).strip()

            # 解析配置参数
            configure_match = re.search(r'configure arguments:([^\n]+)', output, re.IGNORECASE)  # NOSONAR
            if configure_match:
                build_info['build_opts'] = configure_match.group(1).strip()

        return build_info

    except Exception as e:
        logger.error(f'获取Nginx编译信息失败: {e}')
        return {
            'compiler': 'Unknown',
            'compile_time': 'Unknown',
            'build_opts': f'获取编译信息失败: {e}'
        }
