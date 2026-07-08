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


def verify_nginx_installation():
    """
    检查Nginx安装状态

    返回:
        dict: 包含安装状态、路径和建议信息的字典
    """
    try:
        # 检查nginx命令是否存在
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode != 0:
            return {
                'installed': False,
                'suggestion': '请使用包管理器安装Nginx (如: apt install nginx 或 yum install nginx)'
            }

        # 获取nginx路径
        ngx_bin_path = output.stdout.strip()

        # 检查nginx文件是否存在
        if not os.path.exists(ngx_bin_path):
            return {
                'installed': False,
                'suggestion': 'Nginx二进制文件不存在，请重新安装'
            }

        return {
            'installed': True,
            'path': ngx_bin_path
        }

    except Exception as e:
        logger.error(f'检查Nginx安装状态失败: {e}')
        return {
            'installed': False,
            'suggestion': f'检查安装状态时出错: {e}'
        }
