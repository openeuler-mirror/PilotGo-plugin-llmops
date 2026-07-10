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

def dump_logs_to_txt(logs: List[Dict[str, Any]], output_path: str) -> bool:
    """
    导出日志到TXT文件
    
    参数:
        logs: 日志记录列表
        output_path: 输出文件路径
        
    返回:
        bool: 是否导出成功
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for log in logs:
                f.write(log.get('raw_line', '') + '\n')
        return True
    except Exception as e:
        logger.error(f"导出TXT文件失败: {e}")
        return False

def dump_logs_to_csv(logs: List[Dict[str, Any]], output_path: str) -> bool:
    """
    导出日志到CSV文件
    
    参数:
        logs: 日志记录列表
        output_path: 输出文件路径
        
    返回:
        bool: 是否导出成功
    """
    try:
        if not logs:
            return False
        
        # 获取所有可能的字段
        fieldnames = set()
        for log in logs:
            fieldnames.update(log.keys())
        
        # 移除raw_line字段，因为它包含原始行
        fieldnames.discard('raw_line')
        fieldnames = ['raw_line'] + sorted(fieldnames)  # 将raw_line放在第一列
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs:
                writer.writerow(log)
        
        return True
    except Exception as e:
        logger.error(f"导出CSV文件失败: {e}")
        return False

def dump_logs_to_json(logs: List[Dict[str, Any]], output_path: str) -> bool:
    """
    导出日志到JSON文件
    
    参数:
        logs: 日志记录列表
        output_path: 输出文件路径
        
    返回:
        bool: 是否导出成功
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"导出JSON文件失败: {e}")
        return False

def dump_nginx_logs(
    output_format: str = 'txt',
    output_path: Optional[str] = None,
    log_type: str = 'access',
    log_format: str = 'combined',
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    ip_address: Optional[str] = None,
    url_pattern: Optional[str] = None,
    status_code: Optional[str] = None,
    max_lines: int = 10000
) -> Dict[str, Any]:
    """
    导出Nginx日志的主函数
    
    参数:
        output_format: 输出格式 ('txt', 'csv', 'json')
        output_path: 输出文件路径
        log_type: 日志类型 ('access', 'error')
        log_format: 日志格式 ('combined', 'main', 或自定义格式名称)
        start_time: 开始时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)
        end_time: 结束时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)
        ip_address: IP地址过滤
        url_pattern: URL模式过滤 (支持正则表达式)
        status_code: 状态码过滤
        max_lines: 最大导出行数
        
    返回:
        dict: 导出结果信息
    """
    output = {
        'success': False,
        'message': '',
        'exported_count': 0,
        'output_path': '',
        'file_size': 0
    }
    
    try:
        # 检查Nginx安装
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            output['message'] = f"Nginx未安装: {nginx_check['suggestion']}"
            return output
        
        # 验证输出格式
        if output_format not in ['txt', 'csv', 'json']:
            output['message'] = f"不支持的输出格式: {output_format}"
            return output
        
        # 设置默认输出路径
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_filename = f"nginx_{log_type}_logs_{timestamp}.{output_format}"
            output_path = os.path.join('/tmp', default_filename)  # NOSONAR
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 获取日志文件
        log_files = fetch_log_files(log_type)
        if not log_files:
            output['message'] = f"未找到{log_type}日志文件"
            return output
        
        # 解析时间范围
        start_dt, end_dt = analyze_time_range(start_time, end_time)
        
        # 读取和解析日志
        all_logs = []
        total_lines_read = 0
        
        for log_file in log_files:
            if total_lines_read >= max_lines:
                break
            
            lines = load_log_file(log_file['path'], max_lines - total_lines_read)
            total_lines_read += len(lines)
            
            for line in lines:
                parsed_log = analyze_log_line(line, log_format)
                if parsed_log:
                    all_logs.append(parsed_log)
        
        # 过滤日志
        filtered_logs = filter_logs(
            all_logs, 
            ip_address, 
            url_pattern, 
            status_code, 
            start_dt, 
            end_dt
        )
        
        if not filtered_logs:
            output['message'] = "未找到匹配的日志记录"
            return output
        
        # 导出日志
        export_success = False
        if output_format == 'txt':
            export_success = dump_logs_to_txt(filtered_logs, output_path)
        elif output_format == 'csv':
            export_success = dump_logs_to_csv(filtered_logs, output_path)
        elif output_format == 'json':
            export_success = dump_logs_to_json(filtered_logs, output_path)
        
        if export_success:
            file_size = os.path.getsize(output_path)
            output.update({
                'success': True,
                'message': f"成功导出 {len(filtered_logs)} 条日志记录",
                'exported_count': len(filtered_logs),
                'output_path': output_path,
                'file_size': file_size
            })
        else:
            output['message'] = "导出文件失败"
        
    except Exception as e:
        logger.error(f"导出Nginx日志失败: {e}")
        output['message'] = f"导出失败: {e}"
    
    return output

# MCP工具配置
TOOL_CONFIG = {
    "name": "dump_nginx_logs",
    "function": dump_nginx_logs,
    "description": "将指定过滤条件的Nginx日志导出为txt/csv/json格式，支持指定存储路径",
    "version": "1.0.0",
    "parameters": {
        "type": "object",
        "properties": {
            "output_format": {
                "type": "string",
                "enum": ["txt", "csv", "json"],
                "description": "输出格式",
                "default": "txt"
            },
            "output_path": {
                "type": "string",
                "description": "输出文件路径，如果不指定则使用默认路径",
                "default": ""
            },
            "log_type": {
                "type": "string",
                "enum": ["access", "error"],
                "description": "日志类型",
                "default": "access"
            },
            "log_format": {
                "type": "string",
                "description": "日志格式名称 (combined, main 或自定义格式)",
                "default": "combined"
            },
            "start_time": {
                "type": "string",
                "description": "开始时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)",
                "default": ""
            },
            "end_time": {
                "type": "string",
                "description": "结束时间 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD)",
                "default": ""
            },
            "ip_address": {
                "type": "string",
                "description": "IP地址过滤 (支持部分匹配)",
                "default": ""
            },
            "url_pattern": {
                "type": "string",
                "description": "URL模式过滤 (支持正则表达式)",
                "default": ""
            },
            "status_code": {
                "type": "string",
                "description": "状态码过滤 (如: 200, 404, 500)",
                "default": ""
            },
            "max_lines": {
                "type": "integer",
                "description": "最大导出行数",
                "default": 10000
            }
        },
        "required": ["output_format"]
    },
    "examples": [
        {
            "name": "dump_nginx_logs",
            "parameters": {
                "output_format": "txt",
                "log_type": "access",
                "max_lines": 1000
            }
        },
        {
            "name": "dump_nginx_logs",
            "parameters": {
                "output_format": "csv",
                "log_type": "error",
                "start_time": "2024-01-01",
                "end_time": "2024-01-31",
                "max_lines": 5000
            }
        },
        {
            "name": "dump_nginx_logs",
            "parameters": {
                "output_format": "json",
                "log_type": "access",
                "ip_address": "192.168.1.100",  # NOSONAR
                "max_lines": 2000
            }
        }
    ]
}
