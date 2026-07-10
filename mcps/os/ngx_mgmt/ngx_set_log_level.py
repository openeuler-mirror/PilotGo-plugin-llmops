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

def modify_error_log_level(cfg_filepath: str, log_level: str, scope: str = 'main', 
                          server_index: int = 0) -> Tuple[bool, str]:
    """
    修改错误日志级别
    
    参数:
        cfg_filepath: 配置文件路径
        log_level: 日志级别
        scope: 作用域 (main/http/server)
        server_index: server块索引（仅当scope为server时有效）
        
    返回:
        tuple: (是否成功, 修改后的内容)
    """
    try:
        if not os.path.exists(cfg_filepath):
            return False, "配置文件不存在"
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        original_content = body
        
        # 验证日志级别
        if log_level not in SUPPORTED_LOG_LEVELS:
            return False, f"不支持的日志级别: {log_level}"
        
        if scope == 'main':
            # 修改主配置块中的error_log
            pattern = r'(error_log\s+[^;\n]+)(?:\s+(?:debug|info|notice|warn|error|crit|alert|emerg))?;'  # NOSONAR
            replacement = rf'\1 {log_level};'
            body = re.sub(pattern, replacement, body)  # NOSONAR
        
        elif scope == 'http':
            # 修改http块中的error_log
            http_pattern = r'(http\s*\{[^}]*?error_log\s+[^;\n]+)(?:\s+(?:debug|info|notice|warn|error|crit|alert|emerg))?;'  # NOSONAR
            
            def replace_http_level(match):
                http_block = match.group(0)
                new_block = re.sub(  # NOSONAR
                    r'(error_log\s+[^;\n]+)(?:\s+(?:debug|info|notice|warn|error|crit|alert|emerg))?;',  # NOSONAR
                    rf'\1 {log_level};',  # NOSONAR
                    http_block  # NOSONAR
                    )  # NOSONAR
                return new_block
            
            body = re.sub(http_pattern, replace_http_level, body, flags=re.DOTALL)  # NOSONAR
        
        elif scope == 'server':
            # 修改指定server块中的error_log
            server_pattern = r'server\s*\{[^}]+\}'  # NOSONAR
            server_matches = list(re.finditer(server_pattern, body, re.DOTALL))  # NOSONAR
            
            if server_index < len(server_matches):
                server_match = server_matches[server_index]
                server_block = server_match.group(0)
                
                new_server_block = re.sub(  # NOSONAR
                    r'(error_log\s+[^;\n]+)(?:\s+(?:debug|info|notice|warn|error|crit|alert|emerg))?;',  # NOSONAR
                    rf'\1 {log_level};',  # NOSONAR
                    server_block  # NOSONAR
                )
                
                body = body[:server_match.start()] + new_server_block + body[server_match.end():]
            else:
                return False, f"找不到索引为 {server_index} 的server块"
        
        # 检查是否实际进行了修改
        if body == original_content:
            # 如果没有找到现有的error_log指令，需要添加
            if scope == 'main':
                # 在主配置块末尾添加error_log指令
                default_log_path = '/var/log/nginx/error.log'
                error_log_line = f'error_log {default_log_path} {log_level};'
                
                # 在events块之前或文件末尾添加
                events_pattern = r'events\s*\{'  # NOSONAR
                events_match = re.search(events_pattern, body)  # NOSONAR
                if events_match:
                    insert_pos = events_match.start()
                    body = body[:insert_pos] + error_log_line + '\n' + body[insert_pos:]
                else:
                    body += '\n' + error_log_line + '\n'
            elif scope == 'http':
                # 在http块内添加error_log指令
                http_pattern = r'(http\s*\{)'  # NOSONAR
                http_match = re.search(http_pattern, body)  # NOSONAR
                if http_match:
                    insert_pos = http_match.end()
                    default_log_path = '/var/log/nginx/error.log'
                    error_log_line = f'    error_log {default_log_path} {log_level};\n'
                    body = body[:insert_pos] + error_log_line + body[insert_pos:]
                else:
                    return False, "找不到http块，无法添加error_log指令"
            
            elif scope == 'server':
                # 在指定server块内添加error_log指令
                server_pattern = r'server\s*\{[^}]+\}'  # NOSONAR
                server_matches = list(re.finditer(server_pattern, body, re.DOTALL))  # NOSONAR
                
                if server_index < len(server_matches):
                    server_match = server_matches[server_index]
                    server_block = server_match.group(0)
                    
                    # 在server块内第一行后添加error_log指令
                    first_brace = server_block.find('{') + 1
                    default_log_path = '/var/log/nginx/error.log'
                    error_log_line = f'    error_log {default_log_path} {log_level};\n'
                    
                    new_server_block = server_block[:first_brace] + error_log_line + server_block[first_brace:]
                    body = body[:server_match.start()] + new_server_block + body[server_match.end():]
                else:
                    return False, f"找不到索引为 {server_index} 的server块"
        
        return True, body
        
    except Exception as e:
        logger.error(f"修改错误日志级别失败: {e}")
        return False, f"修改失败: {e}"

def deactivate_debug_log(cfg_filepath: str) -> Tuple[bool, str]:
    """
    关闭debug日志（将debug级别提升为info）
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        tuple: (是否成功, 修改后的内容)
    """
    try:
        if not os.path.exists(cfg_filepath):
            return False, "配置文件不存在"
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 将所有debug级别的error_log替换为info级别
        pattern = r'(error_log\s+[^;\n]+)\s+debug;'  # NOSONAR
        replacement = r'\1 info;'
        new_content = re.sub(pattern, replacement, body)  # NOSONAR
        
        # 检查是否进行了修改
        if new_content == body:
            return True, "未找到debug级别的日志配置，无需修改"
        
        return True, new_content
        
    except Exception as e:
        logger.error(f"关闭debug日志失败: {e}")
        return False, f"关闭debug日志失败: {e}"