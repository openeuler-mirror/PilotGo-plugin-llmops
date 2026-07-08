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


def fetch_nginx_version():
    """
    获取Nginx版本信息

    返回:
        dict: 包含主版本和详细版本信息的字典
    """
    try:
        # 获取版本信息
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        ver_data = {
            'main_version': 'Unknown',
            'full_version': 'Unknown'
        }

        if output.returncode == 0:
            output = output.stdout.strip()
            # 解析版本信息
            ver_match = re.search(r'nginx/([\d\.]+)', output)  # NOSONAR
            if ver_match:
                ver_data['main_version'] = ver_match.group(1)
                ver_data['full_version'] = output

            # 如果stdout没有，尝试stderr
            if ver_data['main_version'] == 'Unknown':
                error_output = output.stderr.strip() if output.stderr else ''
                ver_match = re.search(r'nginx/([\d\.]+)', error_output)  # NOSONAR
                if ver_match:
                    ver_data['main_version'] = ver_match.group(1)
                    ver_data['full_version'] = error_output

        return ver_data

    except Exception as e:
        logger.error(f'获取Nginx版本信息失败: {e}')
        return {
            'main_version': 'Unknown',
            'full_version': f'获取版本信息失败: {e}'
        }
