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

def activate_debug_log(cfg_filepath: str, scope: str = 'main', 
                    server_index: int = 0, log_path: str = None) -> Tuple[bool, str]:
    """
    开启debug日志
    
    参数:
        cfg_filepath: 配置文件路径
        scope: 作用域
        server_index: server块索引
        log_path: 日志文件路径
        
    返回:
        tuple: (是否成功, 修改后的内容)
    """
    try:
        if not os.path.exists(cfg_filepath):
            return False, "配置文件不存在"
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        log_path = '/var/log/nginx/debug.log' if log_path is None else log_path
        debug_log_line = f'error_log {log_path} debug;'
        
        if scope == 'main':
            # 在主配置块中添加或修改debug日志配置
            pattern = r'(error_log\s+[^;\n]+)(?:\s+(?:debug|info|notice|warn|error|crit|alert|emerg))?;'  # NOSONAR
            
            def replace_with_debug(match):
                existing_config = match.group(1)
                # 如果已经是指定的日志路径，则只修改级别
                return f'{existing_config} debug;' if log_path in existing_config else match.group(0) + f'\n{debug_log_line}'
            
            body = re.sub(pattern, replace_with_debug, body)  # NOSONAR
            
            # 如果没有找到任何error_log指令，直接添加
            if 'error_log' not in body:
                body = debug_log_line + '\n' + body
        
        elif scope == 'http':
            # 在http块中添加debug日志配置
            http_pattern = r'(http\s*\{)'  # NOSONAR
            http_match = re.search(http_pattern, body)  # NOSONAR
            if http_match:
                insert_pos = http_match.end()
                body = body[:insert_pos] + f'\n    {debug_log_line}' + body[insert_pos:]
            else:
                return False, "找不到http块"
        
        elif scope == 'server':
            # 在指定server块中添加debug日志配置
            server_pattern = r'server\s*\{[^}]+\}'  # NOSONAR
            server_matches = list(re.finditer(server_pattern, body, re.DOTALL))  # NOSONAR
            
            if server_index < len(server_matches):
                server_match = server_matches[server_index]
                server_block = server_match.group(0)
                
                first_brace = server_block.find('{') + 1
                new_server_block = server_block[:first_brace] + f'\n    {debug_log_line}' + server_block[first_brace:]
                body = body[:server_match.start()] + new_server_block + body[server_match.end():]
            else:
                return False, f"找不到索引为 {server_index} 的server块"
        
        return True, body
        
    except Exception as e:
        logger.error(f"开启debug日志失败: {e}")
        return False, f"开启debug日志失败: {e}"

def verify_nginx_syntax(config_content: str) -> Tuple[bool, str]:
    """
    检查Nginx配置语法
    
    参数:
        config_content: 配置内容
        
    返回:
        tuple: (语法是否正确, 错误信息)
    """
    try:
        # 创建临时文件
        temp_file = '/tmp/nginx_temp.conf'  # NOSONAR
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # 检查语法
        output = subprocess.run(['nginx', '-t', '-c', temp_file], 
                              capture_output=True, text=True)
        
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if output.returncode == 0:
            return True, "语法检查通过"
        else:
            err_text = output.stderr if output.stderr else output.stdout
            return False, err_text
            
    except Exception as e:
        logger.error(f"检查Nginx语法失败: {e}")
        return False, f"语法检查失败: {e}"

def reload_nginx_config() -> Tuple[bool, str]:
    """
    重新加载Nginx配置
    
    返回:
        tuple: (是否成功, 消息)
    """
    try:
        # 尝试平滑重载
        output = subprocess.run(['nginx', '-s', 'reload'], 
                              capture_output=True, text=True)
        
        if output.returncode == 0:
            return True, "Nginx配置重载成功"
        else:
            err_text = output.stderr if output.stderr else output.stdout
            return False, f"重载失败: {err_text}"
            
    except Exception as e:
        logger.error(f"重载Nginx配置失败: {e}")
        return False, f"重载失败: {e}"

def set_nginx_log_level(log_level: str = None, disable_debug: bool = False, 
                       enable_debug: bool = False, scope: str = 'main',
                       server_index: int = 0, debug_log_path: str = None,
                       reload_config: bool = True) -> str:
    """
    设置Nginx错误日志级别
    
    参数:
        log_level: 要设置的日志级别
        disable_debug: 是否关闭debug日志
        enable_debug: 是否开启debug日志
        scope: 作用域 (main/http/server)
        server_index: server块索引
        debug_log_path: debug日志文件路径
        reload_config: 是否重载配置
        
    返回:
        str: JSON格式的操作结果
    """
    try:
        # 检查Nginx安装状态
        if not verify_nginx_installation():
            return json.dumps({
                'status': 'error',
                'message': 'Nginx未安装或未正确配置',
                'suggestion': '请先安装并配置Nginx'
            }, ensure_ascii=False, indent=2)
        
        # 获取Nginx配置路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return json.dumps({
                'status': 'error',
                'message': '无法找到Nginx配置文件',
                'suggestion': '请检查Nginx配置'
            }, ensure_ascii=False, indent=2)
        
        # 备份配置文件
        backup_path = save_config_file(cfg_filepath)
        
        # 获取当前配置
        current_config = fetch_current_error_log_config(cfg_filepath)
        
        result_info = {
            'status': 'success',
            'config_file': cfg_filepath,
            'backup_file': backup_path,
            'current_config': current_config,
            'changes': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # 读取原始配置内容
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        new_content = original_content
        
        # 执行请求的操作
        if disable_debug:
            success, body = deactivate_debug_log(cfg_filepath)
            if success:
                new_content = body
                result_info['changes'].append('关闭了debug日志')
            else:
                result_info['status'] = 'error'
                result_info['message'] = body
                return json.dumps(result_info, ensure_ascii=False, indent=2)
        
        elif enable_debug:
            success, body = activate_debug_log(cfg_filepath, scope, server_index, debug_log_path)
            if success:
                new_content = body
                result_info['changes'].append('开启了debug日志')
            else:
                result_info['status'] = 'error'
                result_info['message'] = body
                return json.dumps(result_info, ensure_ascii=False, indent=2)
        
        elif log_level:
            success, body = modify_error_log_level(cfg_filepath, log_level, scope, server_index)
            if success:
                new_content = body
                result_info['changes'].append(f'将{scope}作用域的日志级别设置为{log_level}')
            else:
                result_info['status'] = 'error'
                result_info['message'] = body
                return json.dumps(result_info, ensure_ascii=False, indent=2)
        
        # 检查配置是否发生变化
        if new_content == original_content:
            result_info['status'] = 'info'
            result_info['message'] = '配置未发生变化'
            return json.dumps(result_info, ensure_ascii=False, indent=2)
        
        # 语法检查
        syntax_ok, syntax_msg = verify_nginx_syntax(new_content)
        if not syntax_ok:
            result_info['status'] = 'error'
            result_info['message'] = f'语法检查失败: {syntax_msg}'
            # 恢复备份
            shutil.copy2(backup_path, cfg_filepath)
            return json.dumps(result_info, ensure_ascii=False, indent=2)
        
        # 写入新配置
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        result_info['syntax_check'] = 'passed'
        
        # 重载配置
        if reload_config:
            reload_ok, reload_msg = reload_nginx_config()
            if reload_ok:
                result_info['reload_status'] = 'success'
                result_info['reload_message'] = reload_msg
            else:
                result_info['reload_status'] = 'warning'
                result_info['reload_message'] = reload_msg
                result_info['message'] = '配置已更新但重载失败，请手动重载Nginx'
        
        return json.dumps(result_info, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"设置Nginx日志级别失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'设置日志级别失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

# 工具配置
TOOL_CONFIG = {
    'name': 'set_nginx_log_level',
    'description': '设置Nginx错误日志级别（debug/info/warn/error/crit）、关闭/开启debug日志',
    'category': 'Nginx',
    'function': set_nginx_log_level,
    'parameters': {
        'log_level': {
            'type': 'string',
            'description': '要设置的日志级别',
            'required': False,
            'enum': SUPPORTED_LOG_LEVELS
        },
        'disable_debug': {
            'type': 'boolean',
            'description': '是否关闭debug日志',
            'required': False,
            'default': False
        },
        'enable_debug': {
            'type': 'boolean',
            'description': '是否开启debug日志',
            'required': False,
            'default': False
        },
        'scope': {
            'type': 'string',
            'description': '作用域: main(主配置)/http(http块)/server(server块)',
            'required': False,
            'default': 'main',
            'enum': ['main', 'http', 'server']
        },
        'server_index': {
            'type': 'integer',
            'description': 'server块索引（仅当scope为server时有效）',
            'required': False,
            'default': 0
        },
        'debug_log_path': {
            'type': 'string',
            'description': 'debug日志文件路径（仅当开启debug日志时有效）',
            'required': False,
            'default': '/var/log/nginx/debug.log'
        },
        'reload_config': {
            'type': 'boolean',
            'description': '是否自动重载Nginx配置',
            'required': False,
            'default': True
        }
    },
    'examples': [
        {
            'description': '将主配置错误日志级别设置为warn',
            'parameters': {
                'log_level': 'warn'
            }
        },
        {
            'description': '关闭debug日志',
            'parameters': {
                'disable_debug': True
            }
        },
        {
            'description': '在http块中开启debug日志',
            'parameters': {
                'enable_debug': True,
                'scope': 'http',
                'debug_log_path': '/var/log/nginx/http_debug.log'
            }
        },
        {
            'description': '设置第一个server块的错误日志级别为info',
            'parameters': {
                'log_level': 'info',
                'scope': 'server',
                'server_index': 0
            }
        }
    ]
}
