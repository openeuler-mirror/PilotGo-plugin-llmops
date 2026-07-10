from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import datetime
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import ssl

# 导入工具函数
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_ssl')

def fetch_ssl_cert_info(cert_path: str) -> Dict[str, Union[str, bool, int, datetime.datetime]]:
    """
    获取SSL证书信息

    参数:
        cert_path: 证书文件路径

    返回:
        dict: 包含证书信息的字典
    """
    cert_info = {
        'path': cert_path,
        'exists': False,
        'readable': False,
        'valid': False,
        'subject': None,
        'issuer': None,
        'not_before': None,
        'not_after': None,
        'days_until_expiry': None,
        'is_expired': False,
        'serial_number': None,
        'signature_algorithm': None,
        'version': None,
        'error': None
    }

    try:
        # 检查证书文件是否存在
        if not os.path.exists(cert_path):
            cert_info['error'] = '证书文件不存在'
            return cert_info

        cert_info['exists'] = True

        # 检查文件是否可读
        if not os.access(cert_path, os.R_OK):
            cert_info['error'] = '无法读取证书文件'
            return cert_info

        cert_info['readable'] = True

        # 读取证书
        with open(cert_path, 'rb') as f:
            cert_data = f.read()

        # 解析证书
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            cert_info['valid'] = True

            # 获取证书信息
            cert_info['subject'] = cert.subject.rfc4514_string()
            cert_info['issuer'] = cert.issuer.rfc4514_string()
            cert_info['not_before'] = cert.not_valid_before.isoformat()
            cert_info['not_after'] = cert.not_valid_after.isoformat()
            cert_info['serial_number'] = str(cert.serial_number)
            cert_info['signature_algorithm'] = cert.signature_algorithm_oid._name
            cert_info['version'] = cert.version.name

            # 计算剩余有效期
            now = datetime.datetime.now(datetime.timezone.utc)
            expiry_date = cert.not_valid_after
            cert_info['days_until_expiry'] = (expiry_date - now).days
            cert_info['is_expired'] = now > expiry_date

        except Exception as e:
            cert_info['error'] = f'解析证书失败: {e}'

        return cert_info

    except Exception as e:
        logger.error(f'获取SSL证书信息失败: {e}')
        cert_info['error'] = f'获取证书信息失败: {e}'
        return cert_info

def analyze_ssl_config(body: str) -> List[Dict[str, Union[str, int, bool]]]:
    """
    解析SSL配置

    参数:
        body: 配置文件内容

    返回:
        list: 包含SSL配置的字典列表
    """
    ssl_configs = []

    try:
        # 查找所有server块
        server_pattern = r'server\s*\{([^}]+)\}'  # NOSONAR
        server_blocks = re.findall(server_pattern, body, re.DOTALL)  # NOSONAR

        for i, server_block in enumerate(server_blocks):
            server_config = {
                'index': i + 1,
                'ssl_enabled': False,
                'listen_ports': [],
                'server_names': [],
                'ssl_certificate': None,
                'ssl_certificate_key': None,
                'ssl_protocols': None,
                'ssl_ciphers': None,
                'ssl_prefer_server_ciphers': None,
                'ssl_session_timeout': None,
                'ssl_session_cache': None,
                'ssl_session_tickets': None,
                'ssl_stapling': None,
                'ssl_stapling_verify': None,
                'ssl_trusted_certificate': None,
                'ssl_dhparam': None,
                'ssl_ecdh_curve': None,
                'ssl_conf_command': None,
                'http2_enabled': False
            }

            # 检查是否启用SSL
            if re.search(r'ssl\s+on', server_block) or re.search(r'listen\s+.*ssl', server_block):  # NOSONAR
                server_config['ssl_enabled'] = True

            # 获取监听端口
            listen_matches = re.findall(r'listen\s+([^;]+)', server_block)  # NOSONAR
            for listen in listen_matches:
                # 提取端口号
                port_match = re.search(r'(\d+)', listen)  # NOSONAR
                if port_match:
                    port = port_match.group(1)
                    if 'ssl' in listen:
                        port += ' (SSL)'
                    server_config['listen_ports'].append(port)

            # 获取服务器名称
            server_name_matches = re.findall(r'server_name\s+([^;]+)', server_block)  # NOSONAR
            for names in server_name_matches:
                name_list = [name.strip() for name in names.split()]
                server_config['server_names'].extend(name_list)

            # 获取SSL配置项
            ssl_certificate_match = re.search(r'ssl_certificate\s+([^;]+)', server_block)  # NOSONAR
            if ssl_certificate_match:
                server_config['ssl_certificate'] = ssl_certificate_match.group(1).strip()

            ssl_certificate_key_match = re.search(r'ssl_certificate_key\s+([^;]+)', server_block)  # NOSONAR
            if ssl_certificate_key_match:
                server_config['ssl_certificate_key'] = ssl_certificate_key_match.group(1).strip()

            ssl_protocols_match = re.search(r'ssl_protocols\s+([^;]+)', server_block)  # NOSONAR
            if ssl_protocols_match:
                server_config['ssl_protocols'] = ssl_protocols_match.group(1).strip()

            ssl_ciphers_match = re.search(r'ssl_ciphers\s+([^;]+)', server_block)  # NOSONAR
            if ssl_ciphers_match:
                server_config['ssl_ciphers'] = ssl_ciphers_match.group(1).strip()

            ssl_prefer_server_ciphers_match = re.search(r'ssl_prefer_server_ciphers\s+([^;]+)', server_block)  # NOSONAR
            if ssl_prefer_server_ciphers_match:
                server_config['ssl_prefer_server_ciphers'] = ssl_prefer_server_ciphers_match.group(1).strip()

            ssl_session_timeout_match = re.search(r'ssl_session_timeout\s+([^;]+)', server_block)  # NOSONAR
            if ssl_session_timeout_match:
                server_config['ssl_session_timeout'] = ssl_session_timeout_match.group(1).strip()

            ssl_session_cache_match = re.search(r'ssl_session_cache\s+([^;]+)', server_block)  # NOSONAR
            if ssl_session_cache_match:
                server_config['ssl_session_cache'] = ssl_session_cache_match.group(1).strip()

            ssl_session_tickets_match = re.search(r'ssl_session_tickets\s+([^;]+)', server_block)  # NOSONAR
            if ssl_session_tickets_match:
                server_config['ssl_session_tickets'] = ssl_session_tickets_match.group(1).strip()

            ssl_stapling_match = re.search(r'ssl_stapling\s+([^;]+)', server_block)  # NOSONAR
            if ssl_stapling_match:
                server_config['ssl_stapling'] = ssl_stapling_match.group(1).strip()

            ssl_stapling_verify_match = re.search(r'ssl_stapling_verify\s+([^;]+)', server_block)  # NOSONAR
            if ssl_stapling_verify_match:
                server_config['ssl_stapling_verify'] = ssl_stapling_verify_match.group(1).strip()

            ssl_trusted_certificate_match = re.search(r'ssl_trusted_certificate\s+([^;]+)', server_block)  # NOSONAR
            if ssl_trusted_certificate_match:
                server_config['ssl_trusted_certificate'] = ssl_trusted_certificate_match.group(1).strip()

            ssl_dhparam_match = re.search(r'ssl_dhparam\s+([^;]+)', server_block)  # NOSONAR
            if ssl_dhparam_match:
                server_config['ssl_dhparam'] = ssl_dhparam_match.group(1).strip()

            ssl_ecdh_curve_match = re.search(r'ssl_ecdh_curve\s+([^;]+)', server_block)  # NOSONAR
            if ssl_ecdh_curve_match:
                server_config['ssl_ecdh_curve'] = ssl_ecdh_curve_match.group(1).strip()

            ssl_conf_command_match = re.search(r'ssl_conf_command\s+([^;]+)', server_block)  # NOSONAR
            if ssl_conf_command_match:
                server_config['ssl_conf_command'] = ssl_conf_command_match.group(1).strip()

            # 检查是否启用HTTP/2
            if re.search(r'listen\s+.*http2', server_block):  # NOSONAR
                server_config['http2_enabled'] = True

            # 只有启用SSL的server块才添加到结果中
            if server_config['ssl_enabled']:
                ssl_configs.append(server_config)

        return ssl_configs

    except Exception as e:
        logger.error(f'解析SSL配置失败: {e}')
        return []