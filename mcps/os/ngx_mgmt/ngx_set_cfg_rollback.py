from pathlib import Path
from typing import Dict, List, Optional, Tuple
import datetime
import json
import logging
import os
import re
import shutil
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_rollback')

def revert_nginx_config(backup_path: str, target_version: Optional[str] = None) -> Dict:
    """
    回滚配置到指定备份版本（自动校验语法、重载配置）

    参数:
        backup_path: 备份文件或备份目录路径
        target_version: 目标版本标识（时间戳或版本号），如果为None则使用最新版本

    返回:
        Dict: 包含回滚结果的字典
    """
    try:
        # 验证Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'rollback_files': []
            }

        # 获取当前配置路径
        config_paths = fetch_config_paths()
        if config_paths['config_root'] == 'Unknown':
            return {
                'success': False,
                'message': '无法确定Nginx配置根目录',
                'rollback_files': []
            }

        # 验证备份路径
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': f'备份路径不存在: {backup_path}',
                'rollback_files': []
            }

        # 查找目标备份版本
        target_backup = locate_target_backup(backup_path, target_version)
        if not target_backup:
            return {
                'success': False,
                'message': f'未找到指定的备份版本: {target_version}' if target_version else '未找到有效的备份文件',
                'rollback_files': []
            }

        # 备份当前配置（创建回滚点）
        current_backup = save_current_config(config_paths)

        # 执行回滚操作
        rollback_results = perform_rollback(target_backup, config_paths)

        # 语法校验
        syntax_check = certify_nginx_syntax()

        # 如果语法校验失败，自动回滚到之前的状态
        if not syntax_check['success']:
            logger.warning('回滚后语法校验失败，自动恢复原配置')
            recover_from_backup(current_backup, config_paths)
            return {
                'success': False,
                'message': f'回滚后语法校验失败: {syntax_check["error"]}，已自动恢复原配置',
                'rollback_files': rollback_results,
                'syntax_check': syntax_check,
                'original_backup': current_backup
            }

        # 重载配置
        reload_result = reload_nginx_config()

        # 生成回滚报告
        report = produce_rollback_report(rollback_results, target_backup, syntax_check, reload_result)

        return {
            'success': True,
            'message': 'Nginx配置回滚完成',
            'target_version': target_backup.get('version', 'Unknown'),
            'rollback_files': rollback_results,
            'syntax_check': syntax_check,
            'reload_result': reload_result,
            'report': report,
            'original_backup': current_backup,
            'timestamp': datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f'回滚Nginx配置失败: {e}')
        return {
            'success': False,
            'message': f'回滚失败: {e}',
            'rollback_files': []
        }

def verify_nginx_installation() -> Dict:
    """检查Nginx安装状态"""
    try:
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode != 0:
            return {
                'installed': False,
                'suggestion': '请使用包管理器安装Nginx (如: apt install nginx 或 yum install nginx)'
            }

        ngx_bin_path = output.stdout.strip()
        if not os.path.exists(ngx_bin_path):
            return {
                'installed': False,
                'suggestion': 'Nginx二进制文件不存在，请重新安装'
            }

        return {'installed': True, 'path': ngx_bin_path}

    except Exception as e:
        logger.error(f'检查Nginx安装状态失败: {e}')
        return {
            'installed': False,
            'suggestion': f'检查安装状态时出错: {e}'
        }