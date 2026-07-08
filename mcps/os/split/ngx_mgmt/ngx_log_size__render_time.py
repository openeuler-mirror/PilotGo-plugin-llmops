#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_size')


def render_time(delta: timedelta) -> str:
    """
    格式化时间差为人类可读的格式（替代 humanize.naturaltime）
    """
    if delta.days > 365:
        years = delta.days // 365
        return f"{years} 年前"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months} 个月前"
    elif delta.days > 0:
        return f"{delta.days} 天前"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} 小时前"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} 分钟前"
    else:
        return "刚刚"
