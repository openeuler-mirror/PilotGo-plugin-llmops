#!/usr/bin/env python3
"""
Nginx日志配置信息获取工具
获取日志切割规则、保留天数、日志级别、自定义日志格式等配置信息
"""

import os
import re
import json
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_config')

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

def analyze_nginx_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 解析后的配置信息
    """
    settings = {
        'main_config': {},
        'http_config': {},
        'server_configs': [],
        'include_files': []
    }
    
    try:
        if not os.path.exists(cfg_filepath):
            logger.error(f"配置文件不存在: {cfg_filepath}")
            return settings
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析include文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR
        for include in includes:
            include_path = include.strip().strip('"\'')
            if not os.path.isabs(include_path):
                include_path = os.path.join(os.path.dirname(cfg_filepath), include_path)
            settings['include_files'].append(include_path)
        
        # 解析http块
        http_pattern = r'http\s*\{([^}]+)\}'  # NOSONAR
        http_match = re.search(http_pattern, body, re.DOTALL)  # NOSONAR
        if http_match:
            http_content = http_match.group(1)
            settings['http_config'] = analyze_config_block(http_content)
        
        # 解析server块
        server_pattern = r'server\s*\{([^}]+)\}'  # NOSONAR
        server_matches = re.finditer(server_pattern, body, re.DOTALL)  # NOSONAR
        for match in server_matches:
            server_content = match.group(1)
            server_config = analyze_config_block(server_content)
            settings['server_configs'].append(server_config)
        
        # 解析主配置
        main_content = re.sub(r'http\s*\{[^}]+\}', '', body, flags=re.DOTALL)  # NOSONAR
        main_content = re.sub(r'server\s*\{[^}]+\}', '', main_content, flags=re.DOTALL)  # NOSONAR
        settings['main_config'] = analyze_config_block(main_content)
        
    except Exception as e:
        logger.error(f"解析Nginx配置文件失败: {e}")
    
    return settings

def analyze_config_block(body: str) -> Dict[str, Any]:
    """
    解析配置块内容
    
    参数:
        body: 配置块内容
        
    返回:
        dict: 解析后的配置项
    """
    settings = {}
    
    # 解析键值对
    pattern = r'(\w+)\s+([^;]+);'  # NOSONAR
    matches = re.findall(pattern, body)  # NOSONAR
    
    for key, val in matches:
        key = key.strip()
        val = val.strip()
        
        # 处理数组值
        if key in settings:
            if isinstance(settings[key], list):
                settings[key].append(val)
            else:
                settings[key] = [settings[key], val]
        else:
            settings[key] = val
    
    return settings

def fetch_log_rotation_config() -> Dict[str, Any]:
    """
    获取日志轮转配置
    
    返回:
        dict: 日志轮转配置信息
    """
    rotation_config = {
        'logrotate_enabled': False,
        'rotation_frequency': 'unknown',
        'retention_days': 0,
        'logrotate_files': [],
        'custom_scripts': []
    }
    
    try:
        # 检查logrotate配置
        logrotate_dir = '/etc/logrotate.d'
        nginx_logrotate = os.path.join(logrotate_dir, 'nginx')
        
        if os.path.exists(nginx_logrotate):
            rotation_config['logrotate_enabled'] = True
            rotation_config['logrotate_files'].append(nginx_logrotate)
            
            with open(nginx_logrotate, 'r', encoding='utf-8') as f:
                body = f.read()
            
            # 解析轮转频率
            if 'daily' in body:
                rotation_config['rotation_frequency'] = 'daily'
            elif 'weekly' in body:
                rotation_config['rotation_frequency'] = 'weekly'
            elif 'monthly' in body:
                rotation_config['rotation_frequency'] = 'monthly'
            
            # 解析保留天数
            rotate_match = re.search(r'rotate\s+(\d+)', body)  # NOSONAR
            if rotate_match:
                rotation_config['retention_days'] = int(rotate_match.group(1))
            
            # 解析压缩配置
            if 'compress' in body:
                rotation_config['compression_enabled'] = True
            else:
                rotation_config['compression_enabled'] = False
            
            # 解析延迟压缩
            if 'delaycompress' in body:
                rotation_config['delayed_compression'] = True
            else:
                rotation_config['delayed_compression'] = False
        
        # 检查自定义轮转脚本
        custom_scripts = [
            '/etc/cron.daily/logrotate',
            '/etc/cron.weekly/logrotate',
            '/usr/local/bin/nginx-logrotate.sh'
        ]
        
        for script in custom_scripts:
            if os.path.exists(script):
                rotation_config['custom_scripts'].append(script)
        
    except Exception as e:
        logger.error(f"获取日志轮转配置失败: {e}")
    
    return rotation_config

def fetch_log_levels(settings: Dict[str, Any]) -> Dict[str, str]:
    """
    获取日志级别配置
    
    参数:
        settings: 解析后的配置信息
        
    返回:
        dict: 日志级别配置
    """
    log_levels = {
        'error_log_level': 'error',
        'access_log_level': 'info'
    }
    
    try:
        # 检查错误日志级别
        if 'error_log' in settings['main_config']:
            error_log_value = settings['main_config']['error_log']
            if isinstance(error_log_value, list):
                error_log_value = error_log_value[0]
            
            # 解析日志级别
            level_match = re.search(r'\s+(debug|info|notice|warn|error|crit|alert|emerg)$', error_log_value)  # NOSONAR
            if level_match:
                log_levels['error_log_level'] = level_match.group(1)
        
        # 检查HTTP块中的错误日志级别
        if 'error_log' in settings['http_config']:
            error_log_value = settings['http_config']['error_log']
            if isinstance(error_log_value, list):
                error_log_value = error_log_value[0]
            
            level_match = re.search(r'\s+(debug|info|notice|warn|error|crit|alert|emerg)$', error_log_value)  # NOSONAR
            if level_match:
                log_levels['error_log_level'] = level_match.group(1)
        
    except Exception as e:
        logger.error(f"获取日志级别失败: {e}")
    
    return log_levels

def fetch_custom_log_formats(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    获取自定义日志格式
    
    参数:
        settings: 解析后的配置信息
        
    返回:
        list: 自定义日志格式列表
    """
    formats = []
    
    try:
        # 解析HTTP块中的log_format指令
        if 'log_format' in settings['http_config']:
            log_format_value = settings['http_config']['log_format']
            if isinstance(log_format_value, list):
                for fmt in log_format_value:
                    formats.append(analyze_log_format(fmt))
            else:
                formats.append(analyze_log_format(log_format_value))
        
        # 解析include文件中的log_format
        for include_file in settings['include_files']:
            if os.path.exists(include_file):
                with open(include_file, 'r', encoding='utf-8') as f:
                    body = f.read()
                
                format_pattern = r'log_format\s+([^{]+)\{([^}]+)\}'  # NOSONAR
                format_matches = re.finditer(format_pattern, body, re.DOTALL)  # NOSONAR
                
                for match in format_matches:
                    format_name = match.group(1).strip()
                    format_content = match.group(2).strip()
                    formats.append({
                        'name': format_name,
                        'format': format_content,
                        'source_file': include_file
                    })
        
    except Exception as e:
        logger.error(f"获取自定义日志格式失败: {e}")
    
    return formats

def analyze_log_format(format_str: str) -> Dict[str, Any]:
    """
    解析日志格式字符串
    
    参数:
        format_str: 日志格式字符串
        
    返回:
        dict: 解析后的日志格式信息
    """
    format_info = {
        'name': 'ngx_log_cfg',
        'format': format_str,
        'variables': []
    }
    
    try:
        # 解析格式名称
        name_match = re.match(r'(\w+)\s+(.+)', format_str)  # NOSONAR
        if name_match:
            format_info['name'] = name_match.group(1)
            format_content = name_match.group(2)
            format_info['format'] = format_content
            
            # 提取变量
            variables = re.findall(r'\$(\w+)', format_content)  # NOSONAR
            format_info['variables'] = sorted(set(variables))
    
    except Exception as e:
        logger.error(f"解析日志格式失败: {e}")
    
    return format_info

def fetch_log_buffer_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    获取日志缓冲配置
    
    参数:
        settings: 解析后的配置信息
        
    返回:
        dict: 日志缓冲配置
    """
    buffer_config = {
        'buffer_enabled': False,
        'buffer_size': 'unknown',
        'flush_interval': 'unknown'
    }
    
    try:
        # 检查access_log中的buffer参数
        if 'access_log' in settings['http_config']:
            access_log_value = settings['http_config']['access_log']
            if isinstance(access_log_value, list):
                access_log_value = access_log_value[0]
            
            if 'buffer' in access_log_value:
                buffer_config['buffer_enabled'] = True
                
                # 解析缓冲区大小
                size_match = re.search(r'buffer=([\d]+[kKmMgG]?)', access_log_value)  # NOSONAR
                if size_match:
                    buffer_config['buffer_size'] = size_match.group(1)
                
                # 解析刷新间隔
                flush_match = re.search(r'flush=([\d]+[smhd]?)', access_log_value)  # NOSONAR
                if flush_match:
                    buffer_config['flush_interval'] = flush_match.group(1)
        
        # 检查server块中的配置
        for server_config in settings['server_configs']:
            if 'access_log' in server_config:
                access_log_value = server_config['access_log']
                if isinstance(access_log_value, list):
                    access_log_value = access_log_value[0]
                
                if 'buffer' in access_log_value and not buffer_config['buffer_enabled']:
                    buffer_config['buffer_enabled'] = True
                    
                    size_match = re.search(r'buffer=([\d]+[kKmMgG]?)', access_log_value)  # NOSONAR
                    if size_match:
                        buffer_config['buffer_size'] = size_match.group(1)
                    
                    flush_match = re.search(r'flush=([\d]+[smhd]?)', access_log_value)  # NOSONAR
                    if flush_match:
                        buffer_config['flush_interval'] = flush_match.group(1)
    
    except Exception as e:
        logger.error(f"获取日志缓冲配置失败: {e}")
    
    return buffer_config