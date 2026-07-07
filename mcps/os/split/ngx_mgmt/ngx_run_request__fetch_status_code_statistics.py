#!/usr/bin/env python3

from datetime import datetime
from typing import Dict, Optional, List
import json
import logging
import os
import re
import subprocess
import time

import psutil
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_runtime_request')


def fetch_status_code_statistics():
    """获取状态码统计"""
    stats = {
        'success_count': 'N/A',
        'redirect_count': 'N/A',
        'client_error_count': 'N/A',
        'server_error_count': 'N/A',
        'success_rate': 'N/A'
    }

    try:
        # 从访问日志获取状态码统计
        log_stats = fetch_access_log_status_statistics()
        if log_stats:
            stats.update(log_stats)

        return stats

    except Exception as e:
        logger.error(f'获取状态码统计失败: {e}')
        return stats
