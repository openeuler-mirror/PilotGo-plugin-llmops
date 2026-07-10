#!/usr/bin/env python3
"""
Nginx日志切割规则设置工具
支持设置日志切割规则（按大小/时间）、保留天数、是否压缩、切割后通知
"""

import os
import re
import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_rotate')

RETENTION_DAYS = 7

def verify_nginx_installation() -> bool:
    """
    检查Nginx是否已安装
    
    返回:
        bool: Nginx是否已安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx主配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
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

def save_config_file(cfg_filepath: str) -> str:
    """
    备份配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 备份文件路径
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{cfg_filepath}.backup.{timestamp}"
        shutil.copy2(cfg_filepath, backup_path)
        logger.info(f"配置文件已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份配置文件失败: {e}")
        raise

def analyze_nginx_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件，获取日志文件路径
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 解析后的配置信息
    """
    settings = {
        'log_files': [],
        'error_logs': [],
        'access_logs': []
    }
    
    try:
        if not os.path.exists(cfg_filepath):
            return settings
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析错误日志路径
        error_log_pattern = r'error_log\s+([^;\s]+)'  # NOSONAR
        error_logs = re.findall(error_log_pattern, body)  # NOSONAR
        for log_path in error_logs:
            if log_path not in ['stderr', 'syslog']:
                settings['error_logs'].append(log_path.strip('"\''))
        
        # 解析访问日志路径
        access_log_pattern = r'access_log\s+([^;\s]+)'  # NOSONAR
        access_logs = re.findall(access_log_pattern, body)  # NOSONAR
        for log_path in access_logs:
            if log_path not in ['off']:
                settings['access_logs'].append(log_path.strip('"\''))
        
        # 合并所有日志文件
        settings['log_files'] = list(set(settings['error_logs'] + settings['access_logs']))
        
    except Exception as e:
        logger.error(f"解析Nginx配置文件失败: {e}")
    
    return settings