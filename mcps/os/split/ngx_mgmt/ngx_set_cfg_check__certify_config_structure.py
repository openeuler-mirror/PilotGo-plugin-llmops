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


def certify_config_structure(config_path: str) -> Dict:
    """
    验证配置文件结构完整性

    参数:
        config_path: 配置文件路径

    返回:
        Dict: 结构验证结果
    """
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_path, allow_absolute=True)
        if not valid:
            logger.error(f"certify_config_structure: config_path 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'issues': [{'type': 'security_error', 'msg': f'配置文件路径不安全：{error_msg}'}]
            }

        body = Path(config_path).read_text(encoding='utf-8')

        issues = []

        # 检查基本结构
        if 'events' not in body:
            issues.append({
                'type': 'missing_section',
                'section': 'events',
                'severity': 'warning',
                'msg': '缺少events块，建议添加基本的events配置'
            })

        if 'http' not in body:
            issues.append({
                'type': 'missing_section',
                'section': 'http',
                'severity': 'error',
                'msg': '缺少http块，这是必需的配置块'
            })

        # 检查常见的配置问题
        lines = body.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()

            # 检查未闭合的花括号
            if '{' in line and '}' not in line:
                # 检查后续行是否有匹配的}
                brace_count = 1
                for j in range(i, min(i + 10, len(lines))):  # 检查后续10行
                    if '{' in lines[j]:
                        brace_count += 1
                    if '}' in lines[j]:
                        brace_count -= 1
                    if brace_count == 0:
                        break

                if brace_count > 0:
                    issues.append({
                        'type': 'unclosed_brace',
                        'line': i,
                        'severity': 'error',
                        'msg': f'第{i}行可能有未闭合的花括号'
                    })

            # 检查指令后缺少分号
            if line and not line.startswith('#') and not line.endswith(';') and not line.endswith('{') and not line.endswith('}'):
                # 排除空行和注释
                if not re.match(r'^\s*(#|$)', line):  # NOSONAR
                    issues.append({
                        'type': 'missing_semicolon',
                        'line': i,
                        'severity': 'warning',
                        'msg': f'第{i}行可能缺少分号'
                    })

        return {
            'success': len([i for i in issues if i['severity'] == 'error']) == 0,
            'issues': issues,
            'total_issues': len(issues),
            'error_count': len([i for i in issues if i['severity'] == 'error']),
            'warning_count': len([i for i in issues if i['severity'] == 'warning'])
        }

    except Exception as e:
        logger.error(f'验证配置结构失败: {e}')
        return {
            'success': False,
            'issues': [{
                'type': 'validation_error',
                'severity': 'error',
                'msg': f'验证配置结构失败: {e}'
            }],
            'total_issues': 1,
            'error_count': 1,
            'warning_count': 0
        }
