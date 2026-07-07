#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import glob
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_path_modify')


def modify_nginx_log_paths(cfg_filepath: Optional[str] = None,
                          access_log_path: Optional[str] = None,
                          error_log_path: Optional[str] = None,
                          backup_original: bool = True) -> Dict:
    """
    修改访问日志/错误日志的存储路径、文件名称

    参数:
        cfg_filepath: Nginx 配置文件路径，如果为 None 则自动检测
        access_log_path: 新的访问日志路径（包含文件名）
        error_log_path: 新的错误日志路径（包含文件名）
        backup_original: 是否备份原始配置文件

    返回:
        Dict: 包含修改结果的字典
    """
    try:
        # 验证参数
        if not access_log_path and not error_log_path:
            return {
                'success': False,
                'message': '必须提供至少一个日志路径参数',
                'changes_made': [],
                'backup_path': None
            }

        # 安全验证：验证 access_log_path 路径参数（如果提供，允许绝对路径）
        if access_log_path is not None:
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_nginx_log_paths: access_log_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'message': f'访问日志路径不安全：{error_msg}',
                    'changes_made': [],
                    'backup_path': None
                }

        # 安全验证：验证 error_log_path 路径参数（如果提供，允许绝对路径）
        if error_log_path is not None:
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_nginx_log_paths: error_log_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'message': f'错误日志路径不安全：{error_msg}',
                    'changes_made': [],
                    'backup_path': None
                }

        # 检查Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'changes_made': [],
                'backup_path': None
            }

        # 获取配置文件路径
        if not cfg_filepath:
            cfg_filepath = fetch_nginx_config_path()
            if not cfg_filepath:
                return {
                    'success': False,
                    'message': '无法自动检测Nginx配置文件路径',
                    'changes_made': [],
                    'backup_path': None
                }

        # 验证配置文件存在
        if not os.path.exists(cfg_filepath):
            return {
                'success': False,
                'message': f'配置文件不存在: {cfg_filepath}',
                'changes_made': [],
                'backup_path': None
            }

        # 备份原始配置文件
        backup_path = None
        if backup_original:
            backup_path = save_config_file(cfg_filepath)
            if not backup_path:
                return {
                    'success': False,
                    'message': '配置文件备份失败',
                    'changes_made': [],
                    'backup_path': None
                }

        # 读取配置文件内容
        original_content = Path(cfg_filepath).read_text(encoding='utf-8')

        # 解析当前日志配置
        current_logs = analyze_current_log_configs(original_content, cfg_filepath)

        # 修改日志路径
        modified_content, changes = modify_log_paths_in_content(
            original_content,
            access_log_path,
            error_log_path,
            current_logs
        )

        # 如果没有修改，直接返回
        if not changes:
            return {
                'success': True,
                'message': '未检测到需要修改的日志配置',
                'changes_made': [],
                'backup_path': backup_path
            }

        # 写入修改后的配置
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        # 验证配置语法
        syntax_check = verify_nginx_syntax(cfg_filepath)
        if not syntax_check['valid']:
            # 语法错误，恢复备份
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, cfg_filepath)

            return {
                'success': False,
                'message': '配置语法错误，已恢复原始配置',
                'changes_made': changes,
                'backup_path': backup_path,
                'syntax_errors': syntax_check['errors']
            }

        # 创建新的日志目录（如果需要）
        build_log_directories(access_log_path, error_log_path)

        # 重载Nginx配置
        reload_result = reload_nginx_config()

        return {
            'success': True,
            'message': '日志路径修改完成',
            'changes_made': changes,
            'backup_path': backup_path,
            'syntax_check': syntax_check,
            'reload_result': reload_result,
            'new_paths': {
                'access_log': access_log_path,
                'error_log': error_log_path
            }
        }

    except Exception as e:
        logger.error(f'修改日志路径失败: {e}')
        # 发生错误时恢复备份
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, cfg_filepath)
            except Exception as restore_error:
                logger.error(f'恢复备份失败: {restore_error}')

        return {
            'success': False,
            'message': f'修改失败: {e}',
            'changes_made': [],
            'backup_path': backup_path
        }
