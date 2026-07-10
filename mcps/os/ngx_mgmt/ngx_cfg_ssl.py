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