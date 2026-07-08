#!/usr/bin/env python3

from datetime import datetime
import logging
import os
import re
import subprocess

import psutil
import pwd, grp

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_pid')


def fetch_resource_statistics(processes):
    """获取资源使用统计"""
    try:
        total_cpu = sum(p['cpu_percent'] for p in processes if p['cpu_percent'] is not None)
        total_mem = sum(p['memory_percent'] for p in processes if p['memory_percent'] is not None)
        count = len(processes)

        output = [
            f'CPU总使用率: {total_cpu:.1f}%',
            f'内存总使用率: {total_mem:.1f}%',
            f'平均CPU使用率: {total_cpu/count:.1f}%' if count else '0%',
            f'平均内存使用率: {total_mem/count:.1f}%' if count else '0%'
        ]
        return '\n'.join(output)
    except Exception as e:
        logger.error(f'获取资源统计失败: {e}')
        return ''
