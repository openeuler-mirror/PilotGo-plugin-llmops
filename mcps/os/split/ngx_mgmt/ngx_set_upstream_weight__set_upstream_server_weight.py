#!/usr/bin/env python3

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_weight')


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
