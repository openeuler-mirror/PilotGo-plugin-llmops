#!/usr/bin/env python3

import glob
import glob
import logging
import os
import re
import socket
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_port')


def fetch_system_port_status():
    """
    获取系统端口监听状态

    返回:
        list: 系统端口监听信息列表
    """
    try:
        ports = []

        # 使用ss命令获取监听端口
        output = subprocess.run(['ss', '-tulnp'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')[1:]  # 跳过标题行

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 7:
                    protocol = parts[0]
                    state = parts[1]
                    local_addr = parts[4]
                    proc_info = parts[6] if len(parts) > 6 else '-'

                    if state == 'LISTEN':
                        port_info = {
                            'protocol': protocol,
                            'local_addr': local_addr,
                            'state': state,
                            'process': proc_info
                        }

                        # 解析进程信息
                        if proc_info != '-':
                            # 格式通常是 "users:((\"nginx\",pid=1234,fd=8))"
                            pid_match = re.search(r'pid=(\d+)', proc_info)  # NOSONAR
                            if pid_match:
                                port_info['pid'] = pid_match.group(1)

                            # 提取进程名
                            proc_match = re.search(r'\"([^\"]+)\"', proc_info)  # NOSONAR
                            if proc_match:
                                port_info['process_name'] = proc_match.group(1)

                        ports.append(port_info)

        return ports

    except Exception as e:
        logger.error(f'获取系统端口监听状态失败: {e}')
        return []
