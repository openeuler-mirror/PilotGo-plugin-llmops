#!/usr/bin/env python3
"""
Nginx配置项设置工具
实现设置指定配置项取值，支持主配置/站点配置/模块配置精准修改
"""

import os
import re
import shutil
import tempfile
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_item')

def set_config_item(config_type: str, item_name: str, item_value: str, 
                   site_name: str = None, context: str = None, 
                   config_file: str = None, backup: bool = True,
                   reload_config: bool = True, validate_syntax: bool = True) -> Dict:
    """
    设置指定配置项的取值
    
    Args:
        config_type: 配置类型 ("main"|"site"|"module")
        item_name: 配置项名称
        item_value: 配置项值
        site_name: 站点名称 (当config_type为site时使用)
        context: 上下文 ("http"|"server"|"location"等)
        config_file: 指定配置文件路径
        backup: 是否备份配置文件
        reload_config: 是否重载配置
        validate_syntax: 是否验证配置语法
    
    Returns:
        dict: 设置结果
    """
    try:
        output = {
            "success": False,
            "message": "",
            "config_type": config_type,
            "item_name": item_name,
            "item_value": item_value,
            "site_name": site_name,
            "context": context,
            "config_file": config_file,
            "backup_path": "",
            "changes_made": [],
            "validation_result": "",
            "reload_result": "",
            "error": ""
        }
        
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            output["error"] = "Nginx未安装"
            return output
        
        # 获取配置文件路径
        if config_file:
            target_files = [config_file]
        else:
            config_paths = fetch_config_file_paths(config_type, site_name)
            if 'error' in config_paths:
                output["error"] = config_paths['error']
                return output
            target_files = config_paths['config_files']
        
        if not target_files:
            output["error"] = f"未找到{config_type}类型的配置文件"
            return output
        
        # 备份配置文件
        if backup:
            backup_result = save_config_files(target_files)
            if backup_result["success"]:
                output["backup_path"] = backup_result["backup_path"]
            else:
                logger.warning(f"配置备份失败: {backup_result.get('error', '')}")
        
        # 验证配置项值格式
        validation_result = certify_config_value(item_name, item_value)
        if not validation_result["valid"]:
            output["error"] = f"配置项值格式错误: {validation_result.get('error', '')}"
            return output
        
        # 修改配置文件
        changes = []
        for config_file in target_files:
            change_result = modify_config_file(config_file, item_name, item_value, context)
            if change_result["success"]:
                changes.append({
                    "file": config_file,
                    "action": change_result["action"],
                    "old_value": change_result.get("old_value"),
                    "new_value": item_value
                })
            else:
                output["error"] = f"修改文件 {config_file} 失败: {change_result.get('error', '')}"
                return output
        
        output["changes_made"] = changes
        
        # 验证配置语法
        if validate_syntax:
            validation_result = certify_nginx_config()
            output["validation_result"] = validation_result["message"]
            if not validation_result["success"]:
                output["error"] = f"配置语法验证失败: {validation_result.get('error', '')}"
                # 恢复备份
                if backup and output["backup_path"]:
                    restore_result = recover_config_files(target_files, output["backup_path"])
                    if restore_result["success"]:
                        output["message"] = "配置修改已回滚"
                return output
        
        # 重载配置
        if reload_config:
            reload_result = reload_nginx_config()
            output["reload_result"] = reload_result["message"]
            if not reload_result["success"]:
                output["error"] = f"配置重载失败: {reload_result.get('error', '')}"
                # 配置语法正确但重载失败，不进行回滚
                output["success"] = True
                output["message"] = "配置修改成功但重载失败，请手动重载"
                return output
        
        output["success"] = True
        output["message"] = f"配置项 '{item_name}' 已成功设置为 '{item_value}'"
        
        return output
        
    except Exception as e:
        logger.error(f"设置配置项失败: {e}")
        return {
            "success": False,
            "message": f"设置配置项失败: {e}",
            "error": str(e)
        }

def fetch_config_file_paths(config_type: str, site_name: str = None) -> Dict:
    """
    获取配置文件路径
    
    Args:
        config_type: 配置类型
        site_name: 站点名称
    
    Returns:
        dict: 配置文件路径信息
    """
    try:
        # 获取主配置文件路径
        cfg_state = get_nginx_config_info()
        main_config_path = cfg_state.get('config_file', '/etc/nginx/nginx.conf')
        
        output = {
            'main_config': main_config_path,
            'config_files': []
        }
        
        if config_type == "main":
            output['config_files'] = [main_config_path]
        
        elif config_type == "site":
            if not site_name:
                # 如果没有指定站点，返回所有站点配置
                output['config_files'] = fetch_all_site_configs(main_config_path)
            else:
                # 查找指定站点配置
                site_config = locate_site_config(main_config_path, site_name)
                if site_config:
                    output['config_files'] = [site_config]
                else:
                    output['error'] = f"未找到站点 '{site_name}' 的配置文件"
        
        elif config_type == "module":
            # 模块配置通常在主配置文件中
            output['config_files'] = [main_config_path]
        
        return output
        
    except Exception as e:
        logger.error(f'获取配置文件路径失败: {e}')
        return {
            'error': f'获取配置文件路径失败: {e}'
        }