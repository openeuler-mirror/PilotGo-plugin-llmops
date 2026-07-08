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


def fetch_process_tree(processes):
    """获取进程树关系"""
    try:
        output = []
        process_dict = {p['pid']: p for p in processes}

        def build_tree(pid, level=0):
            proc = process_dict.get(pid)
            if not proc: return
            indent = '  ' * level
            output.append(f'{indent}└─ {proc["name"]} (PID: {pid})')
            children = [p for p in processes if p['ppid'] == pid]
            for child in children:
                build_tree(child['pid'], level + 1)

        # 从根进程开始构建
        root_pids = [p['pid'] for p in processes if p['ppid'] not in process_dict or p['ppid'] == 0]
        if root_pids:
            output.append('进程树结构:')
            for pid in root_pids:
                build_tree(pid)
            return '\n'.join(output)
        return ''
    except Exception as e:
        logger.error(f'构建进程树失败: {e}')
        return ''
