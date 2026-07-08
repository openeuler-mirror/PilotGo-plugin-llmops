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


def clear_upstream_fail_stats_nginx_plus(upstream_name: str, server_address: Optional[str] = None) -> Dict[str, Any]:
    """
    通过Nginx Plus API清空失败统计（商业版功能）
    
    参数:
        upstream_name: upstream名称
        server_address: 特定服务器地址（可选）
        
    返回:
        dict: 操作结果
    """
    output = {
        'success': False,
        'message': '',
        'cleared_servers': []
    }
    
    try:
        # 获取当前状态
        status_data = fetch_upstream_status_from_nginx_plus(upstream_name)
        if not status_data:
            output['message'] = "无法获取Nginx Plus状态信息"
            return output
        
        # 构建清空请求
        clear_urls = [
            f"http://127.0.0.1:8080/api/3/http/upstreams/{upstream_name}/peers",  # NOSONAR
            f"http://127.0.0.1:80/api/3/http/upstreams/{upstream_name}/peers"  # NOSONAR
        ]
        
        import requests
        
        for url in clear_urls:
            if verify_url_accessibility(url):
                # 获取所有服务器
                response = requests.get(url)
                if response.status_code == 200:
                    peers = response.json()
                    
                    for peer in peers:
                        peer_id = peer.get('id')
                        peer_addr = peer.get('server')
                        
                        # 如果指定了特定服务器，只处理该服务器
                        if server_address and server_address not in peer_addr:
                            continue
                        
                        # 发送清空请求
                        clear_url = f"{url}/{peer_id}/state"
                        clear_data = {
                            'fails': 0,
                            'unavailable': None
                        }
                        
                        clear_response = requests.patch(clear_url, json=clear_data)
                        if clear_response.status_code == 200:
                            output['cleared_servers'].append(peer_addr)
                    
                    if output['cleared_servers']:
                        output['success'] = True
                        output['message'] = f"成功清空 {len(output['cleared_servers'])} 个服务器的失败统计"
                    else:
                        output['message'] = "未找到匹配的服务器"
                    
                    return output
        
        output['message'] = "Nginx Plus API不可用"
        return output
        
    except Exception as e:
        logger.error(f"清空Nginx Plus失败统计失败: {e}")
        output['message'] = f"清空失败: {e}"
        return output
