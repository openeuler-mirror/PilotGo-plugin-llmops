from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import datetime
import json
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

# 导入工具函数
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_backup_list')

def locate_config_backup_dirs(base_dir: str = None) -> List[str]:
    """
    查找可能的配置备份目录

    参数:
        base_dir: 基础目录，如果为None则使用常见路径

    返回:
        list: 备份目录路径列表
    """
    backup_dirs = []

    try:
        # 常见的备份目录路径
        common_paths = [
            '/etc/nginx/backup',
            '/etc/nginx/backups',
            '/etc/nginx/conf.d/backup',
            '/etc/nginx/conf.d/backups',
            '/usr/local/nginx/conf/backup',
            '/usr/local/nginx/conf/backups',
            '/var/backups/nginx',
            '/var/backups/nginx-config',
            '/opt/nginx/backup',
            '/opt/nginx/backups',
            '/home/nginx/backup',
            '/home/nginx/backups'
        ]

        # 如果指定了基础目录，添加到搜索路径
        if base_dir:
            common_paths.insert(0, os.path.join(base_dir, 'backup'))
            common_paths.insert(1, os.path.join(base_dir, 'backups'))

        # 检查每个路径是否存在
        for path in common_paths:
            if os.path.isdir(path):
                backup_dirs.append(path)

        return backup_dirs

    except Exception as e:
        logger.error(f'查找配置备份目录失败: {e}')
        return []

def locate_config_backup_files(config_dir: str, backup_dirs: List[str]) -> List[Dict[str, Union[str, int, float, datetime.datetime]]]:
    """
    查找配置备份文件

    参数:
        config_dir: 配置文件目录
        backup_dirs: 备份目录列表

    返回:
        list: 备份文件信息列表
    """
    backup_files = []

    try:
        # 在配置目录中查找备份文件
        if os.path.exists(config_dir):
            for file in os.listdir(config_dir):
                file_path = os.path.join(config_dir, file)
                if os.path.isfile(file_path):
                    # 检查文件名是否包含备份标识
                    if is_backup_file(file):
                        backup_info = fetch_backup_file_info(file_path)
                        if backup_info:
                            backup_files.append(backup_info)

        # 在备份目录中查找备份文件
        for backup_dir in backup_dirs:
            if os.path.exists(backup_dir):
                for root, dirs, files in os.walk(backup_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            # 检查文件名是否包含备份标识
                            if is_backup_file(file):
                                backup_info = fetch_backup_file_info(file_path)
                                if backup_info:
                                    backup_files.append(backup_info)

        # 按修改时间排序（最新的在前）
        backup_files.sort(key=lambda x: x.get('modified_time', 0), reverse=True)

        return backup_files

    except Exception as e:
        logger.error(f'查找配置备份文件失败: {e}')
        return []

def is_backup_file(filename: str) -> bool:
    """
    判断文件是否是备份文件

    参数:
        filename: 文件名

    返回:
        bool: 是否是备份文件
    """
    # 常见的备份文件命名模式
    backup_patterns = [
        r'\.bak$',
        r'\.backup$',
        r'\.old$',
        r'\.orig$',
        r'\.save$',
        r'\.tmp$',
        r'\.conf\.\d+$',
        r'\.conf-\d+$',
        r'\.conf_\d+$',
        r'\d{8}-\d{6}',  # 日期时间格式: YYYYMMDD-HHMMSS
        r'\d{4}-\d{2}-\d{2}',  # 日期格式: YYYY-MM-DD
        r'backup-\d+',
        r'bak-\d+',
        r'old-\d+'
    ]

    for pattern in backup_patterns:
        if re.search(pattern, filename, re.IGNORECASE):  # NOSONAR
            return True

    return False

def fetch_backup_file_info(file_path: str) -> Optional[Dict[str, Union[str, int, float, datetime.datetime]]]:
    """
    获取备份文件信息

    参数:
        file_path: 文件路径

    返回:
        dict: 备份文件信息，如果出错则返回None
    """
    try:
        # 获取文件基本信息
        file_stat = os.stat(file_path)
        filename = os.path.basename(file_path)

        # 提取备份时间
        backup_time = derive_backup_time(filename, file_stat.st_mtime)

        # 提取版本备注
        version_note = derive_version_note(filename)

        # 确定文件类型
        file_type = determine_file_type(filename)

        # 获取文件大小（KB）
        size_kb = file_stat.st_size / 1024

        return {
            'path': file_path,
            'filename': filename,
            'file_type': file_type,
            'size_kb': round(size_kb, 2),
            'modified_time': file_stat.st_mtime,
            'modified_datetime': datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'backup_time': backup_time,
            'version_note': version_note,
            'is_readable': os.access(file_path, os.R_OK)
        }

    except Exception as e:
        logger.error(f'获取备份文件信息失败: {e}')
        return None

def derive_backup_time(filename: str, mtime: float) -> Optional[str]:
    """
    从文件名中提取备份时间

    参数:
        filename: 文件名
        mtime: 文件修改时间

    返回:
        str: 备份时间字符串，如果无法提取则返回None
    """
    try:
        # 尝试匹配日期时间格式: YYYYMMDD-HHMMSS
        datetime_match = re.search(r'(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', filename)  # NOSONAR
        if datetime_match:
            year, month, day, hour, minute, second = datetime_match.groups()
            return f"{year}-{month}-{day} {hour}:{minute}:{second}"

        # 尝试匹配日期格式: YYYY-MM-DD
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)  # NOSONAR
        if date_match:
            year, month, day = date_match.groups()
            return f"{year}-{month}-{day}"

        # 尝试匹配日期格式: YYYYMMDD
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)  # NOSONAR
        if date_match:
            year, month, day = date_match.groups()
            return f"{year}-{month}-{day}"

        # 如果无法从文件名提取，使用文件修改时间
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        logger.error(f'提取备份时间失败: {e}')
        return None

def derive_version_note(filename: str) -> str:
    """
    从文件名中提取版本备注

    参数:
        filename: 文件名

    返回:
        str: 版本备注
    """
    try:
        # 尝试匹配版本备注模式
        version_patterns = [
            r'v(\d+\.\d+\.\d+)',  # v1.0.0
            r'version-(\d+)',     # version-1
            r'release-(\d+)',     # release-1
            r'update-(\d+)',      # update-1
            r'(\d{8}-\d{6})',     # 日期时间格式
            r'(\d{4}-\d{2}-\d{2})' # 日期格式
        ]

        for pattern in version_patterns:
            match = re.search(pattern, filename, re.IGNORECASE)  # NOSONAR
            if match:
                return match.group(1)

        # 如果没有匹配到版本号，尝试提取其他信息
        # 移除常见的备份标识
        clean_name = re.sub(r'\.(bak|backup|old|orig|save|tmp)$', '', filename, flags=re.IGNORECASE)  # NOSONAR

        # 如果清理后的名称与原名称不同，说明有备份标识
        if clean_name != filename:
            return f"备份文件 ({clean_name})"

        return "无版本备注"

    except Exception as e:
        logger.error(f'提取版本备注失败: {e}')
        return "提取失败"

def determine_file_type(filename: str) -> str:
    """
    确定配置文件类型

    参数:
        filename: 文件名

    返回:
        str: 文件类型
    """
    try:
        # 检查文件扩展名
        if filename.endswith('.conf'):
            return '配置文件'
        elif filename.endswith('.key'):
            return '私钥文件'
        elif filename.endswith('.crt') or filename.endswith('.pem'):
            return '证书文件'
        elif filename.endswith('.log'):
            return '日志文件'
        elif 'nginx' in filename.lower():
            return 'Nginx配置'
        elif 'ssl' in filename.lower():
            return 'SSL配置'
        elif 'site' in filename.lower() or 'vhost' in filename.lower():
            return '站点配置'
        else:
            return '未知类型'

    except Exception as e:
        logger.error(f'确定文件类型失败: {e}')
        return '未知类型'