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


def verify_port_conflicts(nginx_ports, system_ports):
    """
    检查端口冲突

    参数:
        nginx_ports: Nginx配置的监听端口列表
        system_ports: 系统实际监听端口列表

    返回:
        list: 端口冲突信息列表
    """
    try:
        conflicts = []

        # 创建系统端口映射
        system_port_map = {}
        for sys_port in system_ports:
            if 'local_addr' in sys_port:
                local_addr = sys_port['local_addr']
                if ':' in local_addr:
                    port = local_addr.split(':')[-1]
                    if port not in system_port_map:
                        system_port_map[port] = []
                    system_port_map[port].append(sys_port)

        # 检查Nginx配置端口
        for nginx_port in nginx_ports:
            port = nginx_port['port']
            if port in system_port_map:
                # 检查是否有其他进程占用
                for sys_port in system_port_map[port]:
                    process_name = sys_port.get('process_name', '未知进程')
                    if 'nginx' not in process_name.lower():
                        conflicts.append({
                            'port': port,
                            'nginx_process': nginx_port.get('server_name', 'Nginx'),
                            'other_process': process_name
                        })

        return conflicts

    except Exception as e:
        logger.error(f'检查端口冲突失败: {e}')
        return []
