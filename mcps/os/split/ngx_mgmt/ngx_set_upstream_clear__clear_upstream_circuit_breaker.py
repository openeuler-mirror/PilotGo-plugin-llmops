#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_clear')


def clear_upstream_circuit_breaker(upstream_name: str, server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    重置熔断器状态
    
    参数:
        upstream_name: upstream 名称
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'reset_servers': []
    }
    
    try:
        # 安全验证：验证 upstream_name 标识符参数
        valid, error_msg = validate_identifier_param(upstream_name)
        if not valid:
            logger.error(f"clear_upstream_circuit_breaker: upstream_name 验证失败：{error_msg}")
            output['message'] = f'无效的 upstream 名称：{error_msg}'
            return output
        
        # 安全验证：如果提供 server_address，也进行验证
        if server_address is not None:
            valid, error_msg = validate_identifier_param(server_address)
            if not valid:
                logger.error(f"clear_upstream_circuit_breaker: server_address 验证失败：{error_msg}")
                output['message'] = f'无效的服务器地址：{error_msg}'
                return output
        
        # 方法 1: 通过 Nginx Plus API（商业版）
        plus_result = clear_upstream_fail_stats_nginx_plus(upstream_name, server_address)
        if plus_result['success']:
            return plus_result
        
        # 方法 2: 通过重新加载配置（开源版）
        cfg_filepath = fetch_nginx_config_path()
        if not cfg_filepath:
            output['message'] = "无法获取 Nginx 配置文件路径"
            return output
        
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"clear_upstream_circuit_breaker: cfg_filepath 路径验证失败：{error_msg}")
            output['message'] = f'配置文件路径不安全：{error_msg}'
            return output
        
        # 备份配置文件
        backup_path = f"{cfg_filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        subprocess.run(['cp', cfg_filepath, backup_path], check=True)
        
        # 读取配置内容
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 查找upstream块
        upstream_pattern = rf'upstream\s+{re.escape(upstream_name)}\s*{{([^}}]+)}}'  # NOSONAR
        upstream_match = re.search(upstream_pattern, body, re.DOTALL)  # NOSONAR
        
        if not upstream_match:
            output['message'] = f"未找到upstream配置: {upstream_name}"
            return output
        
        upstream_content = upstream_match.group(1)
        upstream_start = upstream_match.start(1)
        upstream_end = upstream_match.end(1)
        
        # 修改服务器配置，移除down标记
        new_upstream_content = upstream_content
        
        # 处理每个服务器
        server_pattern = r'server\s+([^;]+);'  # NOSONAR
        server_matches = list(re.finditer(server_pattern, upstream_content))  # NOSONAR
        
        for match in reversed(server_matches):  # 从后往前处理，避免位置偏移
            server_config = match.group(1).strip()
            server_parts = server_config.split()
            
            # 如果指定了特定服务器，只处理该服务器
            if server_address and server_address not in server_parts[0]:
                continue
            
            # 移除down标记
            new_server_config = ' '.join([part for part in server_parts if part != 'down'])
            
            # 替换服务器配置
            new_upstream_content = (new_upstream_content[:match.start(1)] + 
                                  new_server_config + 
                                  new_upstream_content[match.end(1):])
            
            output['reset_servers'].append(server_parts[0])
        
        if not output['reset_servers']:
            output['message'] = "未找到匹配的服务器"
            return output
        
        # 替换整个upstream内容
        new_content = body[:upstream_start] + new_upstream_content + body[upstream_end:]
        
        # 写回配置文件
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 检查配置语法
        syntax_check = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if syntax_check.returncode != 0:
            # 恢复备份
            subprocess.run(['cp', backup_path, cfg_filepath], check=True)
            output['message'] = f"配置语法错误: {syntax_check.stderr}"
            return output
        
        # 重新加载配置
        reload_result = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)
        if reload_result.returncode == 0:
            output['success'] = True
            output['message'] = f"成功重置 {len(output['reset_servers'])} 个服务器的熔断状态"
        else:
            output['message'] = f"重新加载配置失败: {reload_result.stderr}"
        
        return output
        
    except Exception as e:
        logger.error(f"重置熔断器状态失败: {e}")
        output['message'] = f"重置失败: {e}"
        return output
