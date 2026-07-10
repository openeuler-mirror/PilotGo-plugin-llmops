#!/usr/bin/env python3
"""
Nginx错误日志级别设置工具
支持设置错误日志级别（debug/info/warn/error/crit）、关闭/开启debug日志
"""

import os
import re
import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_level')

# 支持的日志级别
SUPPORTED_LOG_LEVELS = ['debug', 'info', 'notice', 'warn', 'error', 'crit', 'alert', 'emerg']

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

def fetch_current_error_log_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    获取当前错误日志配置
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 当前错误日志配置信息
    """
    current_config = {
        'main_level': 'error',  # 默认级别
        'http_level': None,
        'server_levels': [],
        'error_log_directives': []
    }
    
    try:
        if not os.path.exists(cfg_filepath):
            return current_config
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析主配置块中的error_log指令
        main_pattern = r'error_log\s+([^;\n]+);'  # NOSONAR
        main_matches = re.findall(main_pattern, body)  # NOSONAR
        
        for match in main_matches:
            log_config = match.strip()
            # 解析日志级别
            for level in SUPPORTED_LOG_LEVELS:
                if f' {level}' in log_config or log_config.endswith(level):
                    current_config['main_level'] = level
                    break
            
            current_config['error_log_directives'].append({
                'scope': 'main',
                'config': log_config,
                'level': current_config['main_level']
            })
        
        # 解析http块中的error_log指令
        http_pattern = r'http\s*\{[^}]*error_log\s+([^;\n]+);[^}]*\}'  # NOSONAR
        http_matches = re.finditer(http_pattern, body, re.DOTALL)  # NOSONAR
        
        for match in http_matches:
            http_content = match.group(0)
            error_log_match = re.search(r'error_log\s+([^;\n]+);', http_content)  # NOSONAR
            if error_log_match:
                log_config = error_log_match.group(1).strip()
                level = 'error'  # 默认
                for lvl in SUPPORTED_LOG_LEVELS:
                    if f' {lvl}' in log_config or log_config.endswith(lvl):
                        level = lvl
                        break
                
                current_config['http_level'] = level
                current_config['error_log_directives'].append({
                    'scope': 'http',
                    'config': log_config,
                    'level': level
                })
        
        # 解析server块中的error_log指令
        server_pattern = r'server\s*\{([^}]+)\}'  # NOSONAR
        server_matches = re.finditer(server_pattern, body, re.DOTALL)  # NOSONAR
        
        for i, match in enumerate(server_matches):
            server_content = match.group(1)
            error_log_match = re.search(r'error_log\s+([^;\n]+);', server_content)  # NOSONAR
            if error_log_match:
                log_config = error_log_match.group(1).strip()
                level = 'error'  # 默认
                for lvl in SUPPORTED_LOG_LEVELS:
                    if f' {lvl}' in log_config or log_config.endswith(lvl):
                        level = lvl
                        break
                
                current_config['server_levels'].append({
                    'server_index': i,
                    'level': level,
                    'config': log_config
                })
                current_config['error_log_directives'].append({
                    'scope': f'server_{i}',
                    'config': log_config,
                    'level': level
                })
        
    except Exception as e:
        logger.error(f"获取当前错误日志配置失败: {e}")
    
    return current_config