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


def produce_fix_suggestions(parsed_errors: Dict) -> List[Dict]:
    """生成修复建议"""
    suggestions = []

    try:
        # 处理错误
        for error in parsed_errors['errors']:
            suggestion = produce_single_suggestion(error)
            if suggestion:
                suggestions.append(suggestion)

        # 处理警告
        for warning in parsed_errors['warnings']:
            suggestion = produce_single_suggestion(warning, is_warning=True)
            if suggestion:
                suggestions.append(suggestion)

        return suggestions

    except Exception as e:
        logger.error(f'生成修复建议失败: {e}')
        return []
