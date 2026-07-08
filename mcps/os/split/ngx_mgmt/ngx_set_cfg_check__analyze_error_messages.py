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


def analyze_error_messages(syntax_result: Dict, config_path: str, config_content: Optional[str] = None) -> Dict:
    """解析错误信息"""
    errors = []
    warnings = []

    try:
        # 如果没有错误，直接返回
        if syntax_result['valid']:
            return {'errors': errors, 'warnings': warnings}

        # 获取错误输出
        error_output = syntax_result['stderr'] or syntax_result['stdout']
        if not error_output:
            errors.append({
                'line_number': 0,
                'msg': '未知语法错误',
                'error_type': 'unknown',
                'context': ''
            })
            return {'errors': errors, 'warnings': warnings}

        # 解析错误行
        error_lines = error_output.split('\n')

        for line in error_lines:
            if not line.strip():
                continue

            # 解析常见的错误模式
            error_info = analyze_error_line(line, config_path, config_content)
            if error_info:
                if error_info.get('severity', 'error') == 'warning':
                    warnings.append(error_info)
                else:
                    errors.append(error_info)

        return {'errors': errors, 'warnings': warnings}

    except Exception as e:
        logger.error(f'解析错误信息失败: {e}')
        errors.append({
            'line_number': 0,
            'msg': f'解析错误信息失败: {e}',
            'error_type': 'parse_error',
            'context': ''
        })
        return {'errors': errors, 'warnings': warnings}
