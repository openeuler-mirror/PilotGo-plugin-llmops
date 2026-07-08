#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.cmd_safety_guard import validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(msg)s',
)
logger = logging.getLogger('nginx_set_config_check')


def build_temp_config_file(config_content: str) -> str:
    """创建临时配置文件"""
    try:
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False)
        temp_file.write(config_content)
        temp_file.close()

        return temp_file.name

    except Exception as e:
        logger.error(f'创建临时配置文件失败: {e}')
        raise
