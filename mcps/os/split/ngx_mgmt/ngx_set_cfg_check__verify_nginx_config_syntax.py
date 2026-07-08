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


def verify_nginx_config_syntax(config_path: Optional[str] = None, config_content: Optional[str] = None) -> Dict:
    """
    校验 Nginx 配置文件语法正确性，返回错误信息、错误行号及修复建议

    参数:
        config_path: 配置文件路径，如果提供则检查该文件
        config_content: 配置内容字符串，如果提供则检查该内容

    返回:
        Dict: 包含语法检查结果的字典
    """
    try:
        # 安全验证：验证 config_path 参数（允许绝对路径）
        if config_path is not None:
            valid, error_msg = validate_path_param(config_path, allow_absolute=True)
            if not valid:
                logger.error(f"verify_nginx_config_syntax: config_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'msg': f'配置文件路径不安全：{error_msg}',
                    'errors': [],
                    'warnings': []
                }

        # 验证参数
        if not config_path and not config_content:
            return {
                'success': False,
                'msg': '必须提供配置文件路径或配置内容',
                'errors': [],
                'warnings': []
            }

        # 检查Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'msg': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'errors': [],
                'warnings': []
            }

        # 准备配置文件
        if config_path:
            if not os.path.exists(config_path):
                return {
                    'success': False,
                    'msg': f'配置文件不存在: {config_path}',
                    'errors': [],
                    'warnings': []
                }

            # 检查文件权限
            if not os.access(config_path, os.R_OK):
                return {
                    'success': False,
                    'msg': f'没有读取权限: {config_path}',
                    'errors': [],
                    'warnings': []
                }

            # 使用实际文件路径
            temp_config_path = config_path
            config_type = 'file'

        else:
            # 创建临时文件来检查配置内容
            temp_config_path = build_temp_config_file(config_content)
            config_type = 'body'

        # 执行语法检查
        syntax_result = invoke_syntax_check(temp_config_path)

        # 解析错误信息
        parsed_errors = analyze_error_messages(syntax_result, temp_config_path, config_content)

        # 生成修复建议
        suggestions = produce_fix_suggestions(parsed_errors)

        # 清理临时文件
        if config_type == 'body':
            os.unlink(temp_config_path)

        # 返回结果
        return {
            'success': syntax_result['valid'],
            'msg': '语法检查完成',
            'config_type': config_type,
            'config_path': config_path if config_path else '临时文件',
            'valid': syntax_result['valid'],
            'errors': parsed_errors['errors'],
            'warnings': parsed_errors['warnings'],
            'suggestions': suggestions,
            'check_time': syntax_result['check_time'],
            'nginx_version': syntax_result['nginx_version']
        }

    except Exception as e:
        logger.error(f'语法检查失败: {e}')
        return {
            'success': False,
            'msg': f'语法检查失败: {e}',
            'errors': [],
            'warnings': []
        }
