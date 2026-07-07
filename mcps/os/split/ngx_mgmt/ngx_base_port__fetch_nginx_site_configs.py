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


def fetch_nginx_site_configs(config_file):
    """
    获取Nginx站点配置信息

    参数:
        config_file: Nginx主配置文件路径

    返回:
        list: 虚拟主机配置列表
    """
    try:
        site_configs = []

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
            site_config = {
                'server_name': '默认主机',
                'listen_ports': [],
                'root': '未配置',
                'index': '未配置',
                'ssl_enabled': False,
                'ssl_cert': None,
                'ssl_key': None,
                'locations': []
            }

            # 获取server_name
            server_name_matches = re.findall(r'server_name\s+([^;]+);', server_block)  # NOSONAR
            if server_name_matches:
                server_names = []
                for name_match in server_name_matches:
                    server_names.extend(name_match.strip().split())
                site_config['server_name'] = ', '.join(server_names)

            # 获取listen端口
            listen_matches = re.findall(r'listen\s+([^;]+);', server_block)  # NOSONAR
            for listen_match in listen_matches:
                addr_port = listen_match.strip().split()[0]
                port = addr_port.split(':')[-1] if ':' in addr_port else addr_port
                site_config['listen_ports'].append(port)

            # 获取root目录
            root_match = re.search(r'root\s+([^;]+);', server_block)  # NOSONAR
            if root_match:
                site_config['root'] = root_match.group(1).strip()

            # 获取index文件
            index_match = re.search(r'index\s+([^;]+);', server_block)  # NOSONAR
            if index_match:
                site_config['index'] = index_match.group(1).strip()

            # 检查SSL
            site_config['ssl_enabled'] = 'ssl' in server_block.lower()

            # 获取SSL证书
            ssl_cert_match = re.search(r'ssl_certificate\s+([^;]+);', server_block)  # NOSONAR
            if ssl_cert_match:
                site_config['ssl_cert'] = ssl_cert_match.group(1).strip()

            ssl_key_match = re.search(r'ssl_certificate_key\s+([^;]+);', server_block)  # NOSONAR
            if ssl_key_match:
                site_config['ssl_key'] = ssl_key_match.group(1).strip()

            # 获取location配置
            location_blocks = re.findall(r'location\s+([^{]*)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', server_block, re.DOTALL)  # NOSONAR
            for location_match in location_blocks:
                location_path = location_match[0].strip()
                location_config = location_match[1]

                location_info = {
                    'path': location_path,
                    'proxy_pass': None,
                    'root': None,
                    'index': None
                }

                # 获取proxy_pass
                proxy_pass_match = re.search(r'proxy_pass\s+([^;]+);', location_config)  # NOSONAR
                if proxy_pass_match:
                    location_info['proxy_pass'] = proxy_pass_match.group(1).strip()

                # 获取root
                root_match = re.search(r'root\s+([^;]+);', location_config)  # NOSONAR
                if root_match:
                    location_info['root'] = root_match.group(1).strip()

                # 获取index
                index_match = re.search(r'index\s+([^;]+);', location_config)  # NOSONAR
                if index_match:
                    location_info['index'] = index_match.group(1).strip()

                site_config['locations'].append(location_info)

            site_configs.append(site_config)

        return site_configs

    except Exception as e:
        logger.error(f'获取Nginx站点配置失败: {e}')
        return []
