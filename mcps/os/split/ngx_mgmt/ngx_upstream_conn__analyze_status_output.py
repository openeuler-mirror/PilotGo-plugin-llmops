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


def analyze_status_output(status_text: str) -> Dict[str, Any]:
    """
    解析Nginx状态输出
    
    参数:
        status_text: 状态模块输出文本
        
    返回:
        dict: 解析后的状态信息
    """
    status_info = {
        'active_connections': 0,
        'server_accepts': 0,
        'server_handled': 0,
        'server_requests': 0,
        'reading': 0,
        'writing': 0,
        'waiting': 0
    }
    
    try:
        # 解析标准格式
        lines = status_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if 'Active connections:' in line:
                status_info['active_connections'] = int(line.split(':')[1].strip())
            elif 'server accepts handled requests' in line:
                parts = line.split()
                if len(parts) >= 4:
                    status_info['server_accepts'] = int(parts[3])
                    status_info['server_handled'] = int(parts[4])
                    status_info['server_requests'] = int(parts[5])
            elif 'Reading:' in line:
                parts = line.split()
                status_info['reading'] = int(parts[1])
                status_info['writing'] = int(parts[3])
                status_info['waiting'] = int(parts[5])
        
    except Exception as e:
        logger.error(f"解析状态输出失败: {e}")
    
    return status_info
