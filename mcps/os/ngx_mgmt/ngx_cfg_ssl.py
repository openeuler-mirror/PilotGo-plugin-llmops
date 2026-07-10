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

def fetch_ssl_config_files(main_config_path: str) -> List[str]:
    """
    获取所有包含SSL配置的文件路径

    参数:
        main_config_path: 主配置文件路径

    返回:
        list: 包含SSL配置的文件路径列表
    """
    ssl_config_files = []

    try:
        # 读取主配置文件
        body = Path(main_config_path).read_text()

        # 检查主配置文件是否包含SSL配置
        if re.search(r'ssl\s+', body):  # NOSONAR
            ssl_config_files.append(main_config_path)

        # 查找include指令
        include_patterns = re.findall(r'include\s+([^\s;]+)', body)  # NOSONAR

        for pattern in include_patterns:
            # 处理通配符
            if '*' in pattern:
                # 获取目录路径
                dir_path = os.path.dirname(pattern)
                if not os.path.isabs(dir_path):
                    # 相对路径，基于主配置文件所在目录
                    dir_path = os.path.join(os.path.dirname(main_config_path), dir_path)

                # 获取文件名模式
                file_pattern = os.path.basename(pattern)

                # 查找匹配的文件
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if re.match(file_pattern.replace('*', '.*'), file):  # NOSONAR
                            full_path = os.path.join(dir_path, file)
                            if os.path.isfile(full_path):
                                # 检查文件是否包含SSL配置
                                file_content = Path(full_path).read_text()
                                if re.search(r'ssl\s+', file_content):  # NOSONAR
                                    ssl_config_files.append(full_path)
            else:
                # 具体文件路径
                if not os.path.isabs(pattern):
                    pattern = os.path.join(os.path.dirname(main_config_path), pattern)

                if os.path.isfile(pattern):
                    # 检查文件是否包含SSL配置
                    file_content = Path(pattern).read_text()
                    if re.search(r'ssl\s+', file_content):  # NOSONAR
                        ssl_config_files.append(pattern)

        return ssl_config_files

    except Exception as e:
        logger.error(f'获取SSL配置文件列表失败: {e}')
        return []

def examine_ssl_security(ssl_configs: List[Dict]) -> Dict[str, Union[List, Dict]]:
    """
    分析SSL安全性

    参数:
        ssl_configs: SSL配置列表

    返回:
        dict: 包含安全性分析的字典
    """
    security_analysis = {
        'protocols': {
            'secure': ['TLSv1.2', 'TLSv1.3'],
            'insecure': ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1'],
            'found': set(),
            'issues': []
        },
        'ciphers': {
            'secure': [],
            'insecure': [],
            'found': set(),
            'issues': []
        },
        'certificates': {
            'valid': 0,
            'expired': 0,
            'expiring_soon': 0,  # 30天内过期
            'issues': []
        },
        'other_settings': {
            'ssl_prefer_server_ciphers': {
                'recommended': 'on',
                'found': [],
                'issues': []
            },
            'ssl_session_cache': {
                'recommended': 'shared:SSL:10m',
                'found': [],
                'issues': []
            },
            'ssl_stapling': {
                'recommended': 'on',
                'found': [],
                'issues': []
            },
            'http2': {
                'recommended': 'enabled',
                'found': [],
                'issues': []
            }
        }
    }

    try:
        # 分析协议
        for config in ssl_configs:
            if config.get('ssl_protocols'):
                protocols = config['ssl_protocols'].split()
                for protocol in protocols:
                    security_analysis['protocols']['found'].add(protocol)

                    if protocol in security_analysis['protocols']['insecure']:
                        security_analysis['protocols']['issues'].append(
                            f"不安全的协议: {protocol} (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                        )

        # 分析证书
        for config in ssl_configs:
            if config.get('ssl_certificate'):
                cert_info = fetch_ssl_cert_info(config['ssl_certificate'])

                if cert_info.get('valid'):
                    if cert_info.get('is_expired'):
                        security_analysis['certificates']['expired'] += 1
                        security_analysis['certificates']['issues'].append(
                            f"证书已过期: {config['ssl_certificate']} (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                        )
                    elif cert_info.get('days_until_expiry', 0) <= 30:
                        security_analysis['certificates']['expiring_soon'] += 1
                        security_analysis['certificates']['issues'].append(
                            f"证书即将过期: {config['ssl_certificate']} (剩余天数: {cert_info.get('days_until_expiry')}, 服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                        )
                    else:
                        security_analysis['certificates']['valid'] += 1
                else:
                    security_analysis['certificates']['issues'].append(
                        f"证书无效: {config['ssl_certificate']} (错误: {cert_info.get('error', 'Unknown')}, 服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                    )

        # 分析其他设置
        for config in ssl_configs:
            # ssl_prefer_server_ciphers
            if config.get('ssl_prefer_server_ciphers'):
                security_analysis['other_settings']['ssl_prefer_server_ciphers']['found'].append(config['ssl_prefer_server_ciphers'])
                if config['ssl_prefer_server_ciphers'] != 'on':
                    security_analysis['other_settings']['ssl_prefer_server_ciphers']['issues'].append(
                        f"建议设置 ssl_prefer_server_ciphers 为 on (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                    )

            # ssl_session_cache
            if config.get('ssl_session_cache'):
                security_analysis['other_settings']['ssl_session_cache']['found'].append(config['ssl_session_cache'])
                if 'shared' not in config['ssl_session_cache']:
                    security_analysis['other_settings']['ssl_session_cache']['issues'].append(
                        f"建议使用共享SSL会话缓存 (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                    )

            # ssl_stapling
            if config.get('ssl_stapling'):
                security_analysis['other_settings']['ssl_stapling']['found'].append(config['ssl_stapling'])
                if config['ssl_stapling'] != 'on':
                    security_analysis['other_settings']['ssl_stapling']['issues'].append(
                        f"建议启用SSL证书钉扎 (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                    )

            # http2
            if config.get('http2_enabled'):
                security_analysis['other_settings']['http2']['found'].append('enabled')
            else:
                security_analysis['other_settings']['http2']['issues'].append(
                    f"建议启用HTTP/2以提高性能 (服务器: {', '.join(config.get('server_names', ['Unknown']))})"
                )

        return security_analysis

    except Exception as e:
        logger.error(f'分析SSL安全性失败: {e}')
        return security_analysis