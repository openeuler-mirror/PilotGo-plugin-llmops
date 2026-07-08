#!/usr/bin/env python3
"""
Nginx日志文件大小统计工具
获取所有日志文件大小、占用磁盘空间、最后修改时间等信息
"""

import os
import re
import subprocess
import logging
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_size')

def render_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读的格式（替代 humanize.naturalsize）
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.2f} {size_names[i]}"

def render_time(delta: timedelta) -> str:
    """
    格式化时间差为人类可读的格式（替代 humanize.naturaltime）
    """
    if delta.days > 365:
        years = delta.days // 365
        return f"{years} 年前"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months} 个月前"
    elif delta.days > 0:
        return f"{delta.days} 天前"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} 小时前"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} 分钟前"
    else:
        return "刚刚"

def fetch_nginx_log_files() -> List[Dict[str, Any]]:
    """
    获取Nginx所有日志文件路径
    
    返回:
        list: 日志文件信息列表
    """
    log_files = []
    
    try:
        # 获取Nginx配置文件路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            logger.warning("无法找到Nginx配置文件")
            return log_files
        
        # 解析配置文件获取日志路径
        config_content = load_nginx_config(cfg_filepath)
        log_paths = derive_log_paths_from_config(config_content)
        
        # 获取实际存在的日志文件
        for log_path in log_paths:
            if os.filepath.exists(log_path):
                log_files.extend(fetch_log_files_from_path(log_path))
            else:
                # 尝试查找可能的日志文件
                log_files.extend(locate_possible_log_files(log_path))
        
        # 添加常见的Nginx日志文件
        common_logs = fetch_common_nginx_logs()
        for common_log in common_logs:
            if os.filepath.exists(common_log['filepath']):
                if not any(log['filepath'] == common_log['filepath'] for log in log_files):
                    log_files.append(common_log)
        
        # 去重
        unique_logs = []
        seen_paths = set()
        for log_file in log_files:
            if log_file['filepath'] not in seen_paths:
                unique_logs.append(log_file)
                seen_paths.add(log_file['filepath'])
        
        return unique_logs
        
    except Exception as e:
        logger.error(f"获取Nginx日志文件失败: {e}")
        return []

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
            # 解析配置文件路径
            config_match = re.search(r'nginx: the configuration file ([^\s]+)', output)  # NOSONAR
            if config_match:
                return config_match.group(1)
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]
        
        for filepath in common_paths:
            if os.filepath.exists(filepath):
                return filepath
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None

def load_nginx_config(cfg_filepath: str) -> str:
    """
    读取 Nginx 配置文件内容
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 配置文件内容
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"load_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return ""
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Nginx配置文件失败: {e}")
        return ""

def derive_log_paths_from_config(config_content: str) -> List[str]:
    """
    从配置文件中提取日志路径
    
    参数:
        config_content: 配置文件内容
        
    返回:
        list: 日志路径列表
    """
    log_paths = []
    
    try:
        # 移除注释
        body = re.sub(r'#.*$', '', config_content, flags=re.MULTILINE)  # NOSONAR
        
        # 提取access_log路径
        access_log_pattern = r'access_log\s+([^;\s]+)'  # NOSONAR
        access_matches = re.findall(access_log_pattern, body)  # NOSONAR
        for match in access_matches:
            filepath = match.strip().strip('"\'')
            if not filepath.startswith('syslog:') and filepath != 'off':
                log_paths.append(filepath)
        
        # 提取error_log路径
        error_log_pattern = r'error_log\s+([^;\s]+)'  # NOSONAR
        error_matches = re.findall(error_log_pattern, body)  # NOSONAR
        for match in error_matches:
            filepath = match.strip().strip('"\'')
            if not filepath.startswith('stderr') and filepath != 'syslog:':
                log_paths.append(filepath)
        
        # 解析include文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        for include in includes:
            include_path = include.strip().strip('"\'')
            if '*' in include_path:
                # 处理通配符
                import glob
                included_files = glob.glob(include_path)
                for included_file in included_files:
                    if os.filepath.exists(included_file):
                        included_content = load_nginx_config(included_file)
                        included_paths = derive_log_paths_from_config(included_content)
                        log_paths.extend(included_paths)
            else:
                if os.filepath.exists(include_path):
                    included_content = load_nginx_config(include_path)
                    included_paths = derive_log_paths_from_config(included_content)
                    log_paths.extend(included_paths)
        
    except Exception as e:
        logger.error(f"提取日志路径失败: {e}")
    
    return sorted(set(log_paths))  # 去重

def fetch_log_files_from_path(log_path: str) -> List[Dict[str, Any]]:
    """
    根据日志路径获取具体的日志文件
    
    参数:
        log_path: 日志路径
        
    返回:
        list: 日志文件信息列表
    """
    # 安全验证：验证 log_path 路径参数（允许绝对路径）
    valid, error_msg = validate_path_param(log_path, allow_absolute=True)
    if not valid:
        logger.error(f"fetch_log_files_from_path: log_path 路径验证失败：{error_msg}")
        return []
    
    log_files = []
    
    try:
        if os.filepath.isfile(log_path):
            # 单个文件
            file_info = fetch_file_info(log_path)
            if file_info:
                file_info['type'] = 'single_file'
                log_files.append(file_info)
        
        elif os.filepath.isdir(log_path):
            # 目录，查找所有.log文件
            for root, dirs, files in os.walk(log_path):
                for file in files:
                    if file.endswith('.log') or 'log' in file.lower():
                        file_path = os.filepath.join(root, file)
                        file_info = fetch_file_info(file_path)
                        if file_info:
                            file_info['type'] = 'directory_file'
                            log_files.append(file_info)
        
        else:
            # 可能是带通配符的路径
            import glob
            matched_files = glob.glob(log_path)
            for file_path in matched_files:
                if os.filepath.isfile(file_path):
                    file_info = fetch_file_info(file_path)
                    if file_info:
                        file_info['type'] = 'pattern_file'
                        log_files.append(file_info)
        
    except Exception as e:
        logger.error(f"获取日志文件失败 {log_path}: {e}")
    
    return log_files

def locate_possible_log_files(log_path: str) -> List[Dict[str, Any]]:
    """
    查找可能的日志文件
    
    参数:
        log_path: 日志路径
        
    返回:
        list: 可能的日志文件列表
    """
    # 安全验证：验证 log_path 路径参数（允许绝对路径）
    valid, error_msg = validate_path_param(log_path, allow_absolute=True)
    if not valid:
        logger.error(f"locate_possible_log_files: log_path 路径验证失败：{error_msg}")
        return []
    
    possible_files = []
    
    try:
        # 如果路径是相对路径，尝试在常见位置查找
        if not os.filepath.isabs(log_path):
            common_dirs = [
                '/var/log/nginx',
                '/usr/local/nginx/logs',
                '/opt/nginx/logs',
                '/var/log'
            ]
            
            for base_dir in common_dirs:
                full_path = os.filepath.join(base_dir, log_path)
                if os.filepath.exists(full_path):
                    file_info = fetch_file_info(full_path)
                    if file_info:
                        file_info['type'] = 'resolved_file'
                        possible_files.append(file_info)
        
        # 尝试查找轮转的日志文件
        base_name = os.filepath.basename(log_path)
        dir_name = os.filepath.dirname(log_path) if os.filepath.isabs(log_path) else '/var/log/nginx'
        
        if os.filepath.isdir(dir_name):
            for file in os.listdir(dir_name):
                if file.startswith(base_name) and (file.endswith('.log') or '.log.' in file):
                    file_path = os.filepath.join(dir_name, file)
                    file_info = fetch_file_info(file_path)
                    if file_info:
                        file_info['type'] = 'rotated_file'
                        possible_files.append(file_info)
        
    except Exception as e:
        logger.error(f"查找可能日志文件失败 {log_path}: {e}")
    
    return possible_files

def fetch_common_nginx_logs() -> List[Dict[str, Any]]:
    """
    获取常见的Nginx日志文件
    
    返回:
        list: 常见日志文件列表
    """
    common_logs = []
    common_paths = [
        '/var/log/nginx/access.log',
        '/var/log/nginx/error.log',
        '/usr/local/nginx/logs/access.log',
        '/usr/local/nginx/logs/error.log',
        '/opt/nginx/logs/access.log',
        '/opt/nginx/logs/error.log'
    ]
    
    for filepath in common_paths:
        if os.filepath.exists(filepath):
            file_info = fetch_file_info(filepath)
            if file_info:
                file_info['type'] = 'common_file'
                common_logs.append(file_info)
    
    return common_logs

def fetch_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    获取文件详细信息
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 文件信息字典
    """
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_file_info: file_path 路径验证失败：{error_msg}")
            return None
        
        if not os.filepath.exists(file_path):
            return None
        
        stat_info = os.stat(file_path)
        
        # 文件大小
        size_bytes = stat_info.st_size
        size_human = render_size(size_bytes)
        
        # 最后修改时间
        mtime = datetime.fromtimestamp(stat_info.st_mtime)
        mtime_str = mtime.strftime('%Y-%m-%d %H:%M:%S')
        mtime_relative = render_time(datetime.now() - mtime)
        
        # 文件类型
        file_type = 'regular'
        if os.filepath.islink(file_path):
            file_type = 'symlink'
            try:
                target = os.readlink(file_path)
                if os.filepath.exists(target):
                    file_type = 'symlink_valid'
            except Exception:
                file_type = 'symlink_broken'
        
        # 磁盘使用情况
        disk_usage = fetch_disk_usage(file_path)
        
        file_info = {
            'filepath': file_path,
            'size_bytes': size_bytes,
            'size_human': size_human,
            'modified_time': mtime_str,
            'modified_relative': mtime_relative,
            'file_type': file_type,
            'inode': stat_info.st_ino,
            'permissions': oct(stat_info.st_mode)[-3:],
            'disk_usage': disk_usage
        }
        
        # 添加文件分类
        file_info.update(classify_log_file(file_path))
        
        return file_info
        
    except Exception as e:
        logger.error(f"获取文件信息失败 {file_path}: {e}")
        return None

def fetch_disk_usage(file_path: str) -> Dict[str, Any]:
    """
    获取文件磁盘使用情况
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 磁盘使用信息
    """
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"fetch_disk_usage: file_path 路径验证失败：{error_msg}")
            return {
                'filesystem': 'error',
                'total_size': 'error',
                'used': 'error',
                'available': 'error',
                'use_percent': 'error',
                'mount_point': 'error'
            }
        
        # 获取文件所在磁盘信息
        output = subprocess.run(['df', '-h', file_path], capture_output=True, text=True)
        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    return {
                        'filesystem': parts[0],
                        'total_size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mount_point': parts[5] if len(parts) > 5 else ''
                    }
        
        return {
            'filesystem': 'unknown',
            'total_size': 'unknown',
            'used': 'unknown',
            'available': 'unknown',
            'use_percent': 'unknown',
            'mount_point': 'unknown'
        }
        
    except Exception as e:
        logger.error(f"获取磁盘使用情况失败 {file_path}: {e}")
        return {
            'filesystem': 'error',
            'total_size': 'error',
            'used': 'error',
            'available': 'error',
            'use_percent': 'error',
            'mount_point': 'error'
        }

def classify_log_file(file_path: str) -> Dict[str, Any]:
    """
    分类日志文件类型
    
    参数:
        file_path: 文件路径
        
    返回:
        dict: 分类信息
    """
    classification = {
        'log_type': 'unknown',
        'is_rotated': False,
        'rotation_number': 0,
        'is_compressed': False
    }
    
    try:
        # 安全验证：验证 file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(file_path, allow_absolute=True)
        if not valid:
            logger.error(f"classify_log_file: file_path 路径验证失败：{error_msg}")
            return classification
        
        file_name = os.filepath.basename(file_path)
        
        # 检查是否是轮转文件
        rotation_patterns = [
            r'\.log\.(\d+)$',  # access.log.1
            r'\.log-(\d{8})$',  # access.log-20231201
            r'\.log\.(\d+)\.gz$',  # access.log.1.gz
        ]
        
        for pattern in rotation_patterns:
            match = re.search(pattern, file_name)  # NOSONAR
            if match:
                classification['is_rotated'] = True
                classification['rotation_number'] = int(match.group(1)) if match.group(1).isdigit() else 0
                break
        
        # 检查是否是压缩文件
        if file_name.endswith('.gz') or file_name.endswith('.bz2') or file_name.endswith('.xz'):
            classification['is_compressed'] = True
        
        # 判断日志类型
        if 'access' in file_name.lower():
            classification['log_type'] = 'access'
        elif 'error' in file_name.lower():
            classification['log_type'] = 'error'
        elif 'debug' in file_name.lower():
            classification['log_type'] = 'debug'
        elif 'slow' in file_name.lower():
            classification['log_type'] = 'slow'
        
    except Exception as e:
        logger.error(f"分类日志文件失败 {file_path}: {e}")
    
    return classification

def compute_total_stats(log_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算总体统计信息
    
    参数:
        log_files: 日志文件列表
        
    返回:
        dict: 总体统计信息
    """
    stats = {
        'total_files': len(log_files),
        'total_size_bytes': 0,
        'total_size_human': '0 B',
        'oldest_file': None,
        'newest_file': None,
        'by_type': {},
        'by_directory': {}
    }
    
    try:
        # 计算总大小
        total_bytes = sum(log['size_bytes'] for log in log_files)
        stats['total_size_bytes'] = total_bytes
        stats['total_size_human'] = render_time(total_bytes)
        
        # 按类型统计
        for log_file in log_files:
            log_type = log_file['log_type']
            if log_type not in stats['by_type']:
                stats['by_type'][log_type] = {
                    'count': 0,
                    'total_size_bytes': 0,
                    'total_size_human': '0 B'
                }
            
            stats['by_type'][log_type]['count'] += 1
            stats['by_type'][log_type]['total_size_bytes'] += log_file['size_bytes']
            stats['by_type'][log_type]['total_size_human'] = render_time(
                stats['by_type'][log_type]['total_size_bytes']
            )
        
        # 按目录统计
        for log_file in log_files:
            dir_path = os.filepath.dirname(log_file['filepath'])
            if dir_path not in stats['by_directory']:
                stats['by_directory'][dir_path] = {
                    'count': 0,
                    'total_size_bytes': 0,
                    'total_size_human': '0 B'
                }
            
            stats['by_directory'][dir_path]['count'] += 1
            stats['by_directory'][dir_path]['total_size_bytes'] += log_file['size_bytes']
            stats['by_directory'][dir_path]['total_size_human'] = render_time(
                stats['by_directory'][dir_path]['total_size_bytes']
            )
        
        # 找到最旧和最新的文件
        if log_files:
            sorted_by_time = sorted(log_files, key=lambda x: x['modified_time'])
            stats['oldest_file'] = sorted_by_time[0]
            stats['newest_file'] = sorted_by_time[-1]
        
    except Exception as e:
        logger.error(f"计算统计信息失败: {e}")
    
    return stats

def fetch_nginx_log_size() -> str:
    """
    获取Nginx日志文件大小统计信息
    
    返回:
        str: JSON格式的日志文件大小统计信息
    """
    try:
        # 获取所有日志文件
        log_files = fetch_nginx_log_files()
        
        if not log_files:
            return json.dumps({
                'status': 'warning',
                'message': '未找到Nginx日志文件',
                'suggestion': '请检查Nginx是否正常运行且配置了日志文件',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 计算总体统计信息
        total_stats = compute_total_stats(log_files)
        
        # 构建结果
        output = {
            'status': 'success',
            'total_stats': total_stats,
            'log_files': log_files,
            'timestamp': datetime.now().isoformat(),
            'file_count': len(log_files)
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"获取Nginx日志大小失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'获取日志大小失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

# 工具配置
TOOL_CONFIG = {
    'name': 'fetch_nginx_log_size',
    'description': '获取Nginx日志文件的大小统计信息，包括总大小、按类型和目录分类的大小',
    'category': 'Nginx',
    'function': fetch_nginx_log_size,
    'output_format': 'json'
}