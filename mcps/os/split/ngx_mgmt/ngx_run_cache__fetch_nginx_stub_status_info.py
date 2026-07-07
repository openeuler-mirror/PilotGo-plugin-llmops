#!/usr/bin/env python3

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


def fetch_nginx_stub_status_info():
    """获取Nginx stub_status 模块信息"""
    try:
        # 查找包含 stub_status 的配置
        config_content = fetch_nginx_config_content()
        
        # 匹配 stub_status 配置
        stub_match = re.search(  # NOSONAR
            r'location\s+([^/{}\s]+)\s*\{[^}]*stub_status\s+on',
            config_content, re.IGNORECASE | re.DOTALL  # NOSONAR
        )
        
        if stub_match:
            return {
                'location': stub_match.group(1),
                'full_path': f"http://localhost{stub_match.group(1)}"  # NOSONAR
            }
        
        return None
        
    except Exception as e:
        logger.error(f'获取 stub_status 信息失败: {e}')
        return None
