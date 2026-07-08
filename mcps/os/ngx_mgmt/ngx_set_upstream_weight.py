#!/usr/bin/env python3
"""
Nginx上游服务器权重设置工具
设置指定上游服务器的权重，支持平滑生效
"""

import json
import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_weight')

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx配置文件路径
    
    返回:
        str: Nginx配置文件路径，如果找不到返回None
    """
    try:
        # 检查Nginx进程获取配置文件路径
        for proc in psutil.process_iter(['name', 'cmdline']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                cmdline = proc.info['cmdline'] or []
                for i, arg in enumerate(cmdline):
                    if arg == '-c' and i + 1 < len(cmdline):
                        return cmdline[i + 1]
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf',
            '/etc/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        # 尝试通过nginx -t命令获取配置路径
        try:
            output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, timeout=10)
            if output.returncode == 0:
                for line in output.stderr.split('\n'):
                    if 'nginx.conf' in line:
                        match = re.search(r'file\s+([^\s]+)', line)  # NOSONAR
                        if match:
                            return match.group(1)
        except Exception:
            pass
        
        logger.warning("无法找到Nginx配置文件")
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
        logger.error(f"读取Nginx配置文件失败 {cfg_filepath}: {e}")
        return ""

def store_nginx_config(cfg_filepath: str, body: str) -> bool:
    """
    写入 Nginx 配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        body: 配置文件内容
        
    返回:
        bool: 是否写入成功
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"store_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return False
        
        # 创建备份
        backup_path = f"{cfg_filepath}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 安全验证：验证 backup_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(backup_path, allow_absolute=True)
        if not valid:
            logger.error(f"store_nginx_config: backup_path 路径验证失败：{error_msg}")
            return False
        
        subprocess.run(['cp', cfg_filepath, backup_path], check=True)
        
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(body)
        
        logger.info(f"配置文件已更新，备份保存在: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"写入Nginx配置文件失败 {cfg_filepath}: {e}")
        return False

def locate_upstream_block(body: str, upstream_name: str) -> Tuple[Optional[str], int, int]:
    """
    查找指定upstream配置块
    
    参数:
        body: 配置文件内容
        upstream_name: upstream名称
        
    返回:
        tuple: (upstream块内容, 起始位置, 结束位置)
    """
    try:
        # 查找upstream块
        pattern = rf'upstream\s+{upstream_name}\s*{{([^}}]+)}}'  # NOSONAR
        match = re.search(pattern, body, re.DOTALL)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        upstream_content = match.group(1)
        start_pos = match.start()
        end_pos = match.end()
        
        return upstream_content, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找upstream块失败 {upstream_name}: {e}")
        return None, -1, -1

def locate_server_in_upstream(upstream_content: str, server_address: str) -> Tuple[Optional[str], int, int]:
    """
    在upstream块中查找指定服务器配置
    
    参数:
        upstream_content: upstream块内容
        server_address: 服务器地址
        
    返回:
        tuple: (服务器配置行, 起始位置, 结束位置)
    """
    try:
        # 构建服务器地址匹配模式
        server_pattern = rf'server\s+{re.escape(server_address)}(?:\s+[^;]+)*;'  # NOSONAR
        match = re.search(server_pattern, upstream_content)  # NOSONAR
        
        if not match:
            # 尝试不带端口号的匹配
            address_only = server_address.split(':')[0]
            server_pattern = rf'server\s+{re.escape(address_only)}(?:\s+[^;]+)*;'  # NOSONAR
            match = re.search(server_pattern, upstream_content)  # NOSONAR
        
        if not match:
            return None, -1, -1
        
        server_line = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        return server_line, start_pos, end_pos
        
    except Exception as e:
        logger.error(f"查找服务器配置失败 {server_address}: {e}")
        return None, -1, -1

def analyze_server_config(server_line: str) -> Dict[str, Any]:
    """
    解析服务器配置参数
    
    参数:
        server_line: 服务器配置行
        
    返回:
        dict: 服务器配置信息
    """
    server_info = {
        'address': '',
        'port': 80,
        'weight': 1,
        'max_fails': 1,
        'fail_timeout': '10s',
        'max_conns': 0,
        'backup': False,
        'down': False
    }
    
    try:
        # 提取服务器地址
        parts = server_line.split()
        if len(parts) > 1:
            address_part = parts[1]
            if ':' in address_part:
                addr_parts = address_part.split(':')
                server_info['address'] = addr_parts[0]
                server_info['port'] = int(addr_parts[1]) if addr_parts[1].isdigit() else 80
            else:
                server_info['address'] = address_part
        
        # 解析参数
        for part in parts[2:]:
            part = part.rstrip(';')
            if part == 'backup':
                server_info['backup'] = True
            elif part == 'down':
                server_info['down'] = True
            elif part.startswith('weight='):
                server_info['weight'] = int(part.split('=')[1])
            elif part.startswith('max_fails='):
                server_info['max_fails'] = int(part.split('=')[1])
            elif part.startswith('fail_timeout='):
                server_info['fail_timeout'] = part.split('=')[1]
            elif part.startswith('max_conns='):
                server_info['max_conns'] = int(part.split('=')[1])
        
    except Exception as e:
        logger.error(f"解析服务器配置失败 {server_line}: {e}")
    
    return server_info

def build_server_config(server_info: Dict[str, Any], new_weight: int) -> str:
    """
    构建新的服务器配置行
    
    参数:
        server_info: 服务器配置信息
        new_weight: 新的权重值
        
    返回:
        str: 新的服务器配置行
    """
    try:
        # 构建基础配置
        address = server_info['address']
        if server_info['port'] != 80:
            address = f"{address}:{server_info['port']}"
        
        config_parts = ['server', address]
        
        # 添加权重参数
        config_parts.append(f"weight={new_weight}")
        
        # 添加其他参数
        if server_info['max_fails'] != 1:
            config_parts.append(f"max_fails={server_info['max_fails']}")
        
        if server_info['fail_timeout'] != '10s':
            config_parts.append(f"fail_timeout={server_info['fail_timeout']}")
        
        if server_info['max_conns'] > 0:
            config_parts.append(f"max_conns={server_info['max_conns']}")
        
        if server_info['backup']:
            config_parts.append('backup')
        
        if server_info['down']:
            config_parts.append('down')
        
        return ' '.join(config_parts) + ';'
        
    except Exception as e:
        logger.error(f"构建服务器配置失败: {e}")
        return ""

def verify_nginx_config(cfg_filepath: str) -> bool:
    """
    检查 Nginx 配置语法
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        bool: 配置语法是否正确
    """
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"verify_nginx_config: cfg_filepath 路径验证失败：{error_msg}")
            return False
        
        output = subprocess.run(['nginx', '-t', '-c', cfg_filepath], 
                              capture_output=True, text=True, timeout=30)
        
        if output.returncode == 0:
            logger.info("Nginx配置语法检查通过")
            return True
        else:
            logger.error(f"Nginx配置语法检查失败: {output.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"检查Nginx配置语法失败: {e}")
        return False

def reload_nginx_gracefully() -> bool:
    """
    平滑重载Nginx配置
    
    返回:
        bool: 重载是否成功
    """
    try:
        # 查找Nginx主进程PID
        nginx_pid = None
        for proc in psutil.process_iter(['pid', 'name', 'ppid']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                if proc.info['ppid'] == 1:  # 主进程的父进程是init
                    nginx_pid = proc.info['pid']
                    break
        
        if not nginx_pid:
            logger.error("未找到Nginx主进程")
            return False
        
        # 发送平滑重载信号
        os.kill(nginx_pid, 1)  # NOSONAR 
        logger.info(f"已向Nginx主进程({nginx_pid})发送平滑重载信号")
        
        # 等待重载完成
        time.sleep(2)
        
        # 检查Nginx是否正常运行
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                if proc.info['pid'] == nginx_pid:
                    logger.info("Nginx平滑重载成功")
                    return True
        
        logger.error("Nginx进程在重载后消失")
        return False
        
    except Exception as e:
        logger.error(f"平滑重载Nginx失败: {e}")
        return False

def set_upstream_server_weight(upstream_name: str, server_address: str, weight: int, 
                              graceful_reload: bool = True) -> str:
    """
    设置上游服务器权重
    
    参数:
        upstream_name: upstream 名称
        server_address: 服务器地址（格式：ip:port 或 domain:port）
        weight: 权重值（1-1000）
        graceful_reload: 是否平滑重载 Nginx
        
    返回:
        str: JSON 格式的操作结果
    """
    try:
        # 安全验证：验证 upstream_name 标识符参数
        valid, error_msg = validate_identifier_param(upstream_name)
        if not valid:
            logger.error(f"set_upstream_server_weight: upstream_name 验证失败：{error_msg}")
            return json.dumps({
                'status': 'error',
                'message': f'无效的 upstream 名称：{error_msg}',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 安全验证：验证 server_address 参数（允许 IP、域名格式）
        valid, error_msg = validate_identifier_param(server_address)
        if not valid:
            logger.error(f"set_upstream_server_weight: server_address 验证失败：{error_msg}")
            return json.dumps({
                'status': 'error',
                'message': f'无效的服务器地址：{error_msg}',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 参数验证
        if not upstream_name or not server_address:
            return json.dumps({
                'status': 'error',
                'message': 'upstream_name 和 server_address 不能为空',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        if weight < 1 or weight > 1000:
            return json.dumps({
                'status': 'error',
                'message': '权重值必须在1-1000之间',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 获取Nginx配置路径
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            return json.dumps({
                'status': 'error',
                'message': '无法找到Nginx配置文件',
                'suggestion': '请确保Nginx已安装并配置正确',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 读取配置文件
        body = load_nginx_config(cfg_filepath)
        if not body:
            return json.dumps({
                'status': 'error',
                'message': '无法读取Nginx配置文件',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 查找upstream块
        upstream_content, upstream_start, upstream_end = locate_upstream_block(body, upstream_name)
        if not upstream_content:
            return json.dumps({
                'status': 'error',
                'message': f'未找到名为"{upstream_name}"的upstream配置',
                'suggestion': '请检查upstream名称是否正确',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 查找服务器配置
        server_line, server_start, server_end = locate_server_in_upstream(upstream_content, server_address)
        if not server_line:
            return json.dumps({
                'status': 'error',
                'message': f'在upstream"{upstream_name}"中未找到服务器"{server_address}"',
                'suggestion': '请检查服务器地址是否正确',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 解析当前服务器配置
        server_info = analyze_server_config(server_line)
        if not server_info['address']:
            return json.dumps({
                'status': 'error',
                'message': f'解析服务器配置失败: {server_line}',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 检查权重是否已为目标值
        if server_info['weight'] == weight:
            return json.dumps({
                'status': 'warning',
                'message': f'服务器"{server_address}"的权重已经是{weight}，无需修改',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 构建新的服务器配置
        new_server_line = build_server_config(server_info, weight)
        if not new_server_line:
            return json.dumps({
                'status': 'error',
                'message': '构建新的服务器配置失败',
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        
        # 更新upstream块内容
        new_upstream_content = (upstream_content[:server_start] + 
                               new_server_line + 
                               upstream_content[server_end:])
        
        # 更新配置文件内容
        new_content = (body[:upstream_start] + 
                      f"upstream {upstream_name} {{\n{new_upstream_content}\n}}" + 
                      body[upstream_end:])
        
        # 写入临时文件进行语法检查
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp_file:
            temp_file.write(new_content)
            temp_path = temp_file.name
        
        try:
            # 检查配置语法
            if not verify_nginx_config(temp_path):
                return json.dumps({
                    'status': 'error',
                    'message': '配置语法检查失败，权重设置被取消',
                    'suggestion': '请检查配置修改是否正确',
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            
            # 写入正式配置文件
            if not store_nginx_config(cfg_filepath, new_content):
                return json.dumps({
                    'status': 'error',
                    'message': '写入配置文件失败',
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False, indent=2)
            
            # 平滑重载Nginx
            if graceful_reload:
                if not reload_nginx_gracefully():
                    return json.dumps({
                        'status': 'warning',
                        'message': '权重设置成功，但平滑重载Nginx失败',
                        'suggestion': '请手动重载Nginx配置',
                        'old_weight': server_info['weight'],
                        'new_weight': weight,
                        'timestamp': datetime.now().isoformat()
                    }, ensure_ascii=False, indent=2)
            
            output = {
                'status': 'success',
                'message': f'服务器"{server_address}"权重设置成功',
                'upstream_name': upstream_name,
                'server_address': server_address,
                'old_weight': server_info['weight'],
                'new_weight': weight,
                'graceful_reload': graceful_reload,
                'timestamp': datetime.now().isoformat()
            }
            
            if not graceful_reload:
                output['suggestion'] = '配置已更新，请手动重载Nginx使配置生效'
            
            return json.dumps(output, ensure_ascii=False, indent=2)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"设置上游服务器权重失败: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'设置权重失败: {e}',
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)

# 工具配置
TOOL_CONFIG = {
    'name': 'set_upstream_server_weight',
    'description': '设置指定上游服务器的权重，支持平滑生效',
    'category': 'Nginx',
    'function': set_upstream_server_weight,
    'input_schema': {
        'type': 'object',
        'properties': {
            'upstream_name': {
                'type': 'string',
                'description': 'upstream服务组名称'
            },
            'server_address': {
                'type': 'string',
                'description': '服务器地址（格式：ip:port 或 domain:port）'
            },
            'weight': {
                'type': 'integer',
                'description': '权重值（1-1000）',
                'minimum': 1,
                'maximum': 1000
            },
            'graceful_reload': {
                'type': 'boolean',
                'description': '是否平滑重载Nginx',
                'default': True
            }
        },
        'required': ['upstream_name', 'server_address', 'weight']
    },
    'examples': [
        {
            'description': '设置backend服务组中192.168.1.100:8080服务器的权重为50',
            'input': {
                'upstream_name': 'backend',
                'server_address': '192.168.1.100:8080',  # NOSONAR
                'weight': 50,
                'graceful_reload': True
            }
        },
        {
            'description': '设置api服务组中api.example.com:443服务器的权重为100，不自动重载',
            'input': {
                'upstream_name': 'api',
                'server_address': 'api.example.com:443',
                'weight': 100,
                'graceful_reload': False
            }
        }
    ]
}