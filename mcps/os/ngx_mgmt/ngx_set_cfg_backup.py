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
logger = logging.getLogger('nginx_set_config_backup')

def save_nginx_configs(backup_path: Optional[str] = None) -> Dict:
    """
    备份当前所有Nginx配置文件（按时间戳命名、支持指定备份路径）

    参数:
        backup_path: 指定备份路径，如果为None则使用默认路径

    返回:
        Dict: 包含备份结果的字典
    """
    try:
        # 验证Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'backup_files': []
            }

        # 获取配置路径
        config_paths = fetch_config_paths()
        if config_paths['config_root'] == 'Unknown':
            return {
                'success': False,
                'message': '无法确定Nginx配置根目录',
                'backup_files': []
            }

        # 设置备份路径
        if not backup_path:
            backup_path = build_default_backup_path()

        # 创建备份目录
        backup_dir = build_backup_directory(backup_path)
        if not backup_dir:
            return {
                'success': False,
                'message': f'无法创建备份目录: {backup_path}',
                'backup_files': []
            }

        # 获取所有配置文件
        config_files = gather_all_config_files(config_paths)
        if not config_files:
            return {
                'success': False,
                'message': '未找到任何Nginx配置文件',
                'backup_files': []
            }

        # 执行备份
        backup_results = perform_backup(config_files, backup_dir)

        # 生成备份报告
        report = produce_backup_report(backup_results, backup_dir)

        # 验证备份完整性
        integrity_check = verify_backup_integrity(backup_results, config_files)

        return {
            'success': True,
            'message': f'Nginx配置文件备份完成',
            'backup_path': backup_dir,
            'backup_files': backup_results,
            'report': report,
            'integrity_check': integrity_check,
            'timestamp': datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f'备份Nginx配置失败: {e}')
        return {
            'success': False,
            'message': f'备份失败: {e}',
            'backup_files': []
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