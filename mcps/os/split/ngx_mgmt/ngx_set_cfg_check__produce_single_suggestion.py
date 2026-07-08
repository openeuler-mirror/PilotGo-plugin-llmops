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


def produce_single_suggestion(error_info: Dict, is_warning: bool = False) -> Optional[Dict]:
    """为单个错误/警告生成修复建议"""
    try:
        error_type = error_info.get('error_type', '')
        msg = error_info.get('msg', '')
        line_number = error_info.get('line_number', 0)
        directive = error_info.get('directive', '')

        suggestion_template = {
            'line_number': line_number,
            'error_type': error_type,
            'msg': msg,
            'suggestion': '',
            'severity': 'warning' if is_warning else 'error'
        }

        # 根据错误类型生成具体建议
        if error_type == 'unknown_directive':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的拼写是否正确，或确认该指令在当前Nginx版本中是否可用'

        elif error_type == 'unterminated_directive':
            suggestion_template['suggestion'] = f'在指令 "{directive}" 的末尾添加分号 (;)'

        elif error_type == 'invalid_arguments':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的参数数量和格式是否正确'

        elif error_type == 'invalid_parameter':
            suggestion_template['suggestion'] = f'检查指令 "{directive}" 的参数值是否有效'

        elif error_type == 'host_not_found':
            suggestion_template['suggestion'] = f'确认主机名 "{directive}" 可以正确解析，或使用IP地址替代'

        elif error_type == 'duplicate_config':
            suggestion_template['suggestion'] = f'移除重复的配置项，或合并相同的配置'

        elif 'syntax error' in msg.lower():
            suggestion_template['suggestion'] = '检查配置语法，确保指令格式正确，参数使用恰当'

        elif 'permission denied' in msg.lower():
            suggestion_template['suggestion'] = '检查文件权限，确保Nginx进程有读取配置文件的权限'

        elif 'no such file' in msg.lower():
            suggestion_template['suggestion'] = '检查文件路径是否正确，文件是否存在'

        else:
            # 通用建议
            suggestion_template['suggestion'] = '检查配置语法，参考Nginx官方文档确认指令用法'

        return suggestion_template

    except Exception as e:
        logger.error(f'生成单个修复建议失败: {e}')
        return None
