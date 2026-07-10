#!/usr/bin/env python3
"""
Nginx上游服务配置设置工具
设置上游服务的负载均衡策略、超时时间、重试次数、熔断阈值等配置参数
"""

import os
import re
import logging
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_config')

def verify_nginx_installed() -> bool:
    """
    检查Nginx是否安装
    
    返回:
        bool: 是否安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception as e:
        logger.error(f"检查Nginx安装状态失败: {e}")
        return False