#!/usr/bin/env python3
"""
Nginx日志导出工具
支持将指定过滤条件的日志导出为txt/csv/json格式，支持指定存储路径
"""

import os
import re
import json
import csv
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_export')

# 预定义的日志格式解析器
LOG_FORMAT_PARSERS = {
    'combined': r'^(\S+) - (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)"',
    'main': r'^(\S+) - (\S+) \[([^\]]+)\] "([^"]*)" (\d+) (\d+)',
    'custom': None  # 自定义格式需要动态解析
}

def verify_nginx_installation() -> Dict[str, Any]:
    """
    检查Nginx是否安装
    
    返回:
        dict: 包含安装状态和信息的字典
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        if output.returncode == 0:
            return {
                'installed': True,
                'version': output.stderr.strip() if output.stderr else 'Unknown',
                'suggestion': 'Nginx已正确安装'
            }
        else:
            return {
                'installed': False,
                'version': 'Unknown',
                'suggestion': '请先安装Nginx或检查PATH环境变量'
            }
    except Exception as e:
        return {
            'installed': False,
            'version': 'Unknown',
            'suggestion': f'检查Nginx安装失败: {e}'
        }

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
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
        
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None

def fetch_log_format_info(config_path: str) -> Dict[str, str]:
    """
    获取Nginx日志格式定义
    
    参数:
        config_path: 配置文件路径
        
    返回:
        dict: 日志格式名称到格式字符串的映射
    """
    log_formats = {}
    
    try:
        if not os.path.exists(config_path):
            return log_formats
        
        body = Path(config_path).read_text(encoding='utf-8')
        
        # 解析log_format指令
        log_format_pattern = r'log_format\s+(\w+)\s+([^;]+);'  # NOSONAR
        matches = re.findall(log_format_pattern, body)  # NOSONAR
        
        for name, format_string in matches:
            log_formats[name] = format_string.strip().strip('"\'')
        
        # 检查包含的文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        
        for include in includes:
            include_path = include.strip().strip('"\'')
            if not os.path.isabs(include_path):
                include_path = os.path.join(os.path.dirname(config_path), include_path)
            
            # 处理通配符
            if '*' in include_path:
                import glob
                included_files = glob.glob(include_path)
                for included_file in included_files:
                    if os.path.exists(included_file):
                        included_formats = fetch_log_format_info(included_file)
                        log_formats.update(included_formats)
            elif os.path.exists(include_path):
                included_formats = fetch_log_format_info(include_path)
                log_formats.update(included_formats)
        
    except Exception as e:
        logger.error(f"获取日志格式信息失败: {e}")
    
    return log_formats

def fetch_log_files(log_type: str = 'access') -> List[Dict[str, Any]]:
    """
    获取Nginx日志文件列表
    
    参数:
        log_type: 日志类型 ('access' 或 'error')
        
    返回:
        list: 日志文件信息列表
    """
    log_files = []
    
    try:
        common_log_dirs = ['/var/log/nginx', '/usr/local/nginx/logs', '/var/log']
        
        for log_dir in common_log_dirs:
            if os.path.exists(log_dir):
                # 查找日志文件
                if log_type == 'access':
                    patterns = ['access.log*', 'access_log*', 'nginx-access.log*']
                else:  # error
                    patterns = ['error.log*', 'error_log*', 'nginx-error.log*']
                
                for pattern in patterns:
                    import glob
                    files = glob.glob(os.path.join(log_dir, pattern))
                    for file_path in files:
                        if os.path.isfile(file_path):
                            stat = os.stat(file_path)
                            file_info = {
                                'path': file_path,
                                'type': log_type,
                                'size': stat.st_size,
                                'mtime': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'mtime_timestamp': stat.st_mtime
                            }
                            log_files.append(file_info)
        
        # 按修改时间排序（最新的在前）
        log_files.sort(key=lambda x: x['mtime_timestamp'], reverse=True)
        
    except Exception as e:
        logger.error(f"获取日志文件列表失败: {e}")
    
    return log_files

def analyze_time_range(start_time: Optional[str], end_time: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    解析时间范围
    
    参数:
        start_time: 开始时间字符串
        end_time: 结束时间字符串
        
    返回:
        tuple: (开始时间, 结束时间) 的datetime对象
    """
    start_dt = None
    end_dt = None
    
    try:
        if start_time:
            # 尝试不同的时间格式
            time_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d'
            ]
            
            for time_format in time_formats:
                try:
                    start_dt = datetime.strptime(start_time, time_format)
                    break
                except ValueError:
                    continue
        
        if end_time:
            for time_format in time_formats:
                try:
                    end_dt = datetime.strptime(end_time, time_format)
                    # 如果是日期格式，设置为当天的23:59:59
                    if time_format == '%Y-%m-%d':
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    break
                except ValueError:
                    continue
        
    except Exception as e:
        logger.error(f"解析时间范围失败: {e}")
    
    return start_dt, end_dt

def analyze_log_line(line: str, log_format: str = 'combined') -> Optional[Dict[str, Any]]:
    """
    解析日志行
    
    参数:
        line: 日志行内容
        log_format: 日志格式
        
    返回:
        dict: 解析后的日志字段字典
    """
    try:
        if log_format in LOG_FORMAT_PARSERS:
            pattern = LOG_FORMAT_PARSERS[log_format]
            if pattern:
                match = re.match(pattern, line.strip())  # NOSONAR
                if match:
                    if log_format == 'combined':
                        return {
                            'remote_addr': match.group(1),
                            'remote_user': match.group(2),
                            'time_local': match.group(3),
                            'request': match.group(4),
                            'status': match.group(5),
                            'body_bytes_sent': match.group(6),
                            'http_referer': match.group(7),
                            'http_user_agent': match.group(8),
                            'raw_line': line.strip()
                        }
                    elif log_format == 'main':
                        return {
                            'remote_addr': match.group(1),
                            'remote_user': match.group(2),
                            'time_local': match.group(3),
                            'request': match.group(4),
                            'status': match.group(5),
                            'body_bytes_sent': match.group(6),
                            'raw_line': line.strip()
                        }
        
        # 如果预定义格式不匹配，尝试通用解析
        return {'raw_line': line.strip()}
        
    except Exception as e:
        logger.error(f"解析日志行失败: {e}")
        return {'raw_line': line.strip()}

def filter_logs(logs: List[Dict[str, Any]], 
                ip_address: Optional[str] = None,
                url_pattern: Optional[str] = None,
                status_code: Optional[str] = None,
                start_time: Optional[datetime] = None,
                end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    过滤日志记录
    
    参数:
        logs: 日志记录列表
        ip_address: IP地址过滤
        url_pattern: URL模式过滤
        status_code: 状态码过滤
        start_time: 开始时间
        end_time: 结束时间
        
    返回:
        list: 过滤后的日志记录
    """
    filtered_logs = []
    
    for log in logs:
        # 时间过滤
        if 'time_local' in log:
            try:
                log_time = datetime.strptime(log['time_local'], '%d/%b/%Y:%H:%M:%S %z')
                if start_time and log_time < start_time:
                    continue
                if end_time and log_time > end_time:
                    continue
            except ValueError:
                pass  # 时间解析失败，不过滤
        
        # IP地址过滤
        if ip_address and 'remote_addr' in log:
            if ip_address not in log['remote_addr']:
                continue
        
        # 状态码过滤
        if status_code and 'status' in log:
            if status_code != log['status']:
                continue
        
        # URL模式过滤
        if url_pattern and 'request' in log:
            if not re.search(url_pattern, log['request']):  # NOSONAR
                continue
        
        filtered_logs.append(log)
    
    return filtered_logs

def load_log_file(file_path: str, max_lines: int = 10000) -> List[str]:
    """
    读取日志文件内容
    
    参数:
        file_path: 日志文件路径
        max_lines: 最大读取行数
        
    返回:
        list: 日志行列表
    """
    lines = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                if line.strip():
                    lines.append(line)
    except Exception as e:
        logger.error(f"读取日志文件失败: {file_path}, 错误: {e}")
    
    return lines