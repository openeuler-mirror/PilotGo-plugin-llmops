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


def derive_directive_from_context(context: str) -> str:
    """从错误上下文中提取指令名称"""
    try:
        # 常见的指令模式
        directive_patterns = [
            r'in\s+"([^"]+)"\s+directive',
            r'directive\s+"([^"]+)"',
            r'parameter\s+"([^"]+)"',
        ]

        for pattern in directive_patterns:
            match = re.search(pattern, context, re.IGNORECASE)  # NOSONAR
            if match:
                return match.group(1)

        return 'unknown'

    except Exception:
        return 'unknown'
