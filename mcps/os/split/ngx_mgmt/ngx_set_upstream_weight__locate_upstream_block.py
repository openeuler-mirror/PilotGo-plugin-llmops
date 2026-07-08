#!/usr/bin/env python3

import json
import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_weight')


def locate_upstream_block(body: str, upstream_name: str) -> Tuple[Optional[str], int, int]:
    """
    查找指定upstream配置块
    
    参数:
        body: 配置文件内容
        upstream_name: upstream名称
        
    返回:
        tuple: (upstream块内容, 起始位置, 结束位置)
    """
    try:
        # 查找upstream块
        pattern = rf'upstream\s+{upstream_name}\s*{{([^}}]+)}}'  # NOSONAR
        match = re.search(pattern, body, re.DOTALL)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        upstream_content = match.group(1)
        start_pos = match.start()
        end_pos = match.end()
        
        return upstream_content, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找upstream块失败 {upstream_name}: {e}")
        return None, -1, -1
