#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_clear')


def fetch_upstream_status_from_nginx_plus(upstream_name: str) -> Optional[Dict[str, Any]]:
    """
    从Nginx Plus获取upstream状态（商业版功能）
    
    参数:
        upstream_name: upstream名称
        
    返回:
        dict: upstream状态信息
    """
    try:
        # Nginx Plus状态API
        status_urls = [
            f"http://127.0.0.1:8080/api/3/http/upstreams/{upstream_name}/peers",  # NOSONAR
            f"http://127.0.0.1:80/api/3/http/upstreams/{upstream_name}/peers"  # NOSONAR
        ]
        
        for url in status_urls:
            if verify_url_accessibility(url):
                import requests
                response = requests.get(url)
                if response.status_code == 200:
                    return response.json()
        
        return None
        
    except Exception as e:
        logger.error(f"从Nginx Plus获取状态失败: {e}")
        return None
