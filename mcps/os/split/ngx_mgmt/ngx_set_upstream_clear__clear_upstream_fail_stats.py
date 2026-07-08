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


def clear_upstream_fail_stats(upstream_name: str, operation_type: str = 'reset_circuit_breaker', 
                             server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    清空上游服务器失败统计的主函数
    
    参数:
        upstream_name: upstream名称
        operation_type: 操作类型 ('reset_circuit_breaker', 'clear_fail_stats', 'restore_server')
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果信息
    """
    output = {
        'success': False,
        'message': '',
        'operation': operation_type,
        'upstream_name': upstream_name,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 检查Nginx安装
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            output['message'] = f"Nginx未安装: {nginx_check['suggestion']}"
            return output
        
        # 检查upstream配置是否存在
        upstream_config = fetch_upstream_configuration(upstream_name)
        if not upstream_config:
            output['message'] = f"未找到upstream配置: {upstream_name}"
            return output
        
        # 根据操作类型执行相应操作
        if operation_type == 'reset_circuit_breaker':
            reset_result = clear_upstream_circuit_breaker(upstream_name, server_address)
            output.update(reset_result)
            
        elif operation_type == 'clear_fail_stats':
            # 尝试使用Nginx Plus API
            clear_result = clear_upstream_fail_stats_nginx_plus(upstream_name, server_address)
            if not clear_result['success']:
                # 开源版本通过重置熔断器来间接清空统计
                clear_result = clear_upstream_circuit_breaker(upstream_name, server_address)
                clear_result['message'] = "开源版本通过重置熔断状态间接清空失败统计"
            output.update(clear_result)
            
        elif operation_type == 'restore_server':
            if not server_address:
                output['message'] = "恢复服务器操作需要指定server_address参数"
                return output
            restore_result = recover_failed_server(upstream_name, server_address)
            output.update(restore_result)
            
        else:
            output['message'] = f"不支持的操作类型: {operation_type}"
        
    except Exception as e:
        logger.error(f"清空上游失败统计失败: {e}")
        output['message'] = f"操作失败: {e}"
    
    return output
