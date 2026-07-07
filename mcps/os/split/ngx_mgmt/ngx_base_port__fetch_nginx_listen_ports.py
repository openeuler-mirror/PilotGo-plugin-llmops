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


def fetch_nginx_listen_ports(config_file):
    """
    获取Nginx监听端口配置

    参数:
        config_file: Nginx主配置文件路径

    返回:
        dict: 包含监听端口列表和相关信息的字典
    """
    try:
        listen_ports = []

        # 读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()

        # 包含其他配置文件
        include_files = re.findall(r'include\s+([^;]+);', body)  # NOSONAR
        all_content = body

        for include_pattern in include_files:
            # 处理通配符
            if '*' in include_pattern:
                include_pattern = include_pattern.strip()
                if not include_pattern.startswith('/'):
                    # 相对路径，基于配置文件目录
                    config_dir = os.path.dirname(config_file)
                    include_pattern = os.path.join(config_dir, include_pattern)

                for include_file in glob.glob(include_pattern):
                    if os.path.exists(include_file):
                        try:
                            with open(include_file, 'r', encoding='utf-8') as f:
                                all_content += '\n' + f.read()
                        except Exception as e:
                            logger.warning(f'读取包含文件失败 {include_file}: {e}')

        # 查找server块
        server_blocks = re.findall(r'server\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', all_content, re.DOTALL)  # NOSONAR

        for server_block in server_blocks:
            # 在每个server块中查找listen指令
            listen_matches = re.findall(r'listen\s+([^;]+);', server_block)  # NOSONAR
            server_name_matches = re.findall(r'server_name\s+([^;]+);', server_block)  # NOSONAR

            server_names = []
            for name_match in server_name_matches:
                server_names.extend(name_match.strip().split())

            if not server_names:
                server_names = ['默认主机']

            # 查找SSL配置
            ssl_enabled = 'ssl' in server_block.lower()
            ssl_cert_match = re.search(r'ssl_certificate\s+([^;]+);', server_block)  # NOSONAR
            ssl_key_match = re.search(r'ssl_certificate_key\s+([^;]+);', server_block)  # NOSONAR

            for listen_match in listen_matches:
                listen_config = listen_match.strip()

                # 解析listen配置
                parts = listen_config.split()
                port_info = {
                    'port': '80',  # 默认端口
                    'ip': '*',      # 默认监听所有IP
                    'server_name': server_names[0] if server_names else '默认主机',
                    'ssl_enabled': ssl_enabled,
                    'raw_config': listen_config
                }

                # 提取端口和IP
                addr_port = parts[0]
                if ':' in addr_port:
                    # 指定了IP地址
                    if addr_port.startswith('[') and ']:' in addr_port:
                        # IPv6地址
                        ip, port = addr_port.rsplit(':', 1)
                        port_info['ip'] = ip + ']'
                        port_info['port'] = port
                    else:
                        # IPv4地址
                        ip, port = addr_port.split(':', 1)
                        port_info['ip'] = ip
                        port_info['port'] = port
                else:
                    # 只有端口
                    port_info['port'] = addr_port

                # 检查其他参数
                if 'ssl' in parts:
                    port_info['ssl_enabled'] = True

                # 添加SSL证书信息
                if ssl_cert_match:
                    port_info['ssl_cert'] = ssl_cert_match.group(1).strip()
                if ssl_key_match:
                    port_info['ssl_key'] = ssl_key_match.group(1).strip()

                # 简化IP显示
                if port_info['ip'] == '*':
                    port_info['ip'] = '所有IP'
                elif port_info['ip'] == '0.0.0.0':
                    port_info['ip'] = '所有IPv4'
                elif port_info['ip'] == '[::]':
                    port_info['ip'] = '所有IPv6'

                listen_ports.append(port_info)

        return {
            'listen_ports': listen_ports,
            'total_count': len(listen_ports)
        }

    except Exception as e:
        logger.error(f'获取Nginx监听端口配置失败: {e}')
        return {
            'listen_ports': [],
            'total_count': 0
        }
