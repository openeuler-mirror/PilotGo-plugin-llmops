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


def recover_failed_server(upstream_name: str, server_address: str) -> Dict[str, Any]:
    """
    恢复故障服务器
    
    参数:
        upstream_name: upstream名称
        server_address: 服务器地址
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'restored_server': server_address
    }
    
    try:
        # 先重置熔断状态
        reset_result = clear_upstream_circuit_breaker(upstream_name, server_address)
        
        if reset_result['success']:
            output['success'] = True
            output['message'] = f"成功恢复服务器: {server_address}"
        else:
            output['message'] = reset_result['message']
        
        return output
        
    except Exception as e:
        logger.error(f"恢复故障服务器失败: {e}")
        output['message'] = f"恢复失败: {e}"
        return output
