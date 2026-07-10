#!/usr/bin/env python3
"""
Nginx错误日志级别设置工具
支持设置错误日志级别（debug/info/warn/error/crit）、关闭/开启debug日志
"""

import os
import re
import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_level')

# 支持的日志级别
SUPPORTED_LOG_LEVELS = ['debug', 'info', 'notice', 'warn', 'error', 'crit', 'alert', 'emerg']

def verify_nginx_installation() -> bool:
    """
    检查Nginx是否已安装
    
    返回:
        bool: Nginx是否已安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False