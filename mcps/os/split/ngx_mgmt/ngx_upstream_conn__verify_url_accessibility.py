#!/usr/bin/env python3

import os
import re
import json
import logging
import subprocess
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_upstream_connection')


def verify_url_accessibility(url: str, timeout: int = 5) -> bool:
    """
    检查URL可访问性
    
    参数:
        url: 要检查的URL
        timeout: 超时时间（秒）
        
    返回:
        bool: 是否可访问
    """
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False
