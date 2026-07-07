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


def analyze_size(size_str):
    """解析大小字符串为字节数"""
    try:
        if size_str == 'N/A' or size_str == 'unlimited':
            return 0
        
        # 移除空格并转换为大写
        size_str = size_str.strip().upper()
        
        # 定义单位转换因子
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        # 提取数值和单位
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Z]+)$', size_str)  # NOSONAR
        if not match:
            raise ValueError(f"无法解析大小字符串: {size_str}")
        
        val, unit = match.groups()
        val = float(val)
        
        if unit not in units:
            raise ValueError(f"未知单位: {unit}")
        
        return val * units[unit]
        
    except Exception as e:
        logger.error(f'解析大小字符串失败: {e}')
        return 0
