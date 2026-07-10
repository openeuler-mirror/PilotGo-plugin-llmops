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

def fetch_all_site_configs(main_config_path: str) -> List[str]:
    """
    获取所有站点配置文件路径
    
    Args:
        main_config_path: 主配置文件路径
    
    Returns:
        list: 站点配置文件路径列表
    """
    site_configs = []
    
    try:
        # 读取主配置文件
        with open(main_config_path, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()
        
        # 查找include指令
        include_patterns = re.findall(r'include\s+([^\s;]+)', body)  # NOSONAR
        
        for pattern in include_patterns:
            # 处理通配符
            if '*' in pattern:
                # 获取目录路径
                dir_path = os.path.dirname(pattern)
                if not os.path.isabs(dir_path):
                    # 相对路径，基于主配置文件所在目录
                    dir_path = os.path.join(os.path.dirname(main_config_path), dir_path)
                
                # 获取文件名模式
                file_pattern = os.path.basename(pattern)
                
                # 查找匹配的文件
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if re.match(file_pattern.replace('*', '.*'), file):  # NOSONAR
                            full_path = os.path.join(dir_path, file)
                            if os.path.isfile(full_path):
                                site_configs.append(full_path)
            else:
                # 具体文件路径
                if not os.path.isabs(pattern):
                    pattern = os.path.join(os.path.dirname(main_config_path), pattern)
                
                if os.path.isfile(pattern):
                    site_configs.append(pattern)
        
        # 如果没有找到站点配置，尝试常见路径
        if not site_configs:
            common_paths = [
                '/etc/nginx/sites-enabled/*',
                '/etc/nginx/conf.d/*.conf',
                '/usr/local/nginx/conf/vhosts/*.conf'
            ]
            
            for path_pattern in common_paths:
                dir_path = os.path.dirname(path_pattern)
                file_pattern = os.path.basename(path_pattern)
                
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if re.match(file_pattern.replace('*', '.*'), file):  # NOSONAR
                            full_path = os.path.join(dir_path, file)
                            if os.path.isfile(full_path):
                                site_configs.append(full_path)
        
        return site_configs
        
    except Exception as e:
        logger.error(f'获取站点配置文件列表失败: {e}')
        return []

def locate_site_config(main_config_path: str, site_name: str) -> Optional[str]:
    """
    查找指定站点的配置文件
    
    Args:
        main_config_path: 主配置文件路径
        site_name: 站点名称
    
    Returns:
        str: 站点配置文件路径，如果未找到则返回None
    """
    try:
        # 获取所有站点配置
        site_configs = fetch_all_site_configs(main_config_path)
        
        # 查找匹配的站点配置
        for config_path in site_configs:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                body = f.read()
            
            # 查找server_name指令
            server_names = re.findall(r'server_name\s+([^;]+)', body)  # NOSONAR
            for names in server_names:
                name_list = [name.strip() for name in names.split()]
                if site_name in name_list:
                    return config_path
        
        # 如果没有找到，尝试根据文件名匹配
        for config_path in site_configs:
            filename = os.path.basename(config_path)
            if site_name in filename:
                return config_path
        
        return None
        
    except Exception as e:
        logger.error(f'查找站点配置失败: {e}')
        return None

def certify_config_value(item_name: str, item_value: str) -> Dict:
    """
    验证配置项值格式
    
    Args:
        item_name: 配置项名称
        item_value: 配置项值
    
    Returns:
        dict: 验证结果
    """
    try:
        # 常见配置项验证规则
        validation_rules = {
            'worker_processes': {
                'pattern': r'^(auto|\d+)$',
                'error': '必须是"auto"或正整数'
            },
            'worker_connections': {
                'pattern': r'^\d+$',
                'error': '必须是正整数'
            },
            'keepalive_timeout': {
                'pattern': r'^\d+$',
                'error': '必须是正整数（秒）'
            },
            'client_max_body_size': {
                'pattern': r'^\d+[kmgKMG]?$',
                'error': '必须是数字或带单位（如10m）'
            },
            'sendfile': {
                'pattern': r'^(on|off)$',
                'error': '必须是"on"或"off"'
            },
            'tcp_nopush': {
                'pattern': r'^(on|off)$',
                'error': '必须是"on"或"off"'
            },
            'tcp_nodelay': {
                'pattern': r'^(on|off)$',
                'error': '必须是"on"或"off"'
            },
            'gzip': {
                'pattern': r'^(on|off)$',
                'error': '必须是"on"或"off"'
            },
            'listen': {
                'pattern': r'^(\d+)(?::\d+)?(\s+[a-z]+)*$',
                'error': '必须是端口号或端口号加选项'
            },
            'server_name': {
                'pattern': r'^[a-zA-Z0-9.*_-]+(?:\s+[a-zA-Z0-9.*_-]+)*$',
                'error': '必须是有效的域名或通配符'
            }
        }
        
        rule = validation_rules.get(item_name)
        if rule:
            if not re.match(rule['pattern'], item_value):  # NOSONAR
                return {
                    "valid": False,
                    "error": f"配置项 '{item_name}' 的值 '{item_value}' 格式错误：{rule['error']}"
                }
        
        return {"valid": True}
        
    except Exception as e:
        logger.error(f"验证配置项值失败: {e}")
        return {"valid": False, "error": f"验证失败: {e}"}

def modify_config_file(config_file: str, item_name: str, item_value: str, context: str = None) -> Dict:
    """
    更新配置文件中的配置项
    
    Args:
        config_file: 配置文件路径
        item_name: 配置项名称
        item_value: 配置项值
        context: 上下文
    
    Returns:
        dict: 更新结果
    """
    try:
        # 读取原文件内容
        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()
        
        original_content = body
        
        # 构建配置项模式
        if context:
            # 在指定上下文中查找和替换
            pattern = rf'({context}\s*{{[^}}]*){item_name}\s+([^;\n]+)([^}}]*}})'  # NOSONAR
            replacement = rf'\1{item_name} {item_value}\3'
            
            # 检查是否匹配
            if re.search(pattern, body, re.DOTALL):  # NOSONAR
                body = re.sub(pattern, replacement, body, flags=re.DOTALL)  # NOSONAR
                action = "updated_in_context"
            else:
                # 在上下文中添加新配置项
                pattern = rf'({context}\s*{{)([^}}]*)(}})'  # NOSONAR
                replacement = rf'\1\2    {item_name} {item_value};\n\3'
                body = re.sub(pattern, replacement, body, flags=re.DOTALL)  # NOSONAR
                action = "added_to_context"
        else:
            # 全局查找和替换
            pattern = rf'{item_name}\s+([^;\n]+)'  # NOSONAR
            replacement = f'{item_name} {item_value}'
            
            # 检查是否匹配
            if re.search(pattern, body):  # NOSONAR
                body = re.sub(pattern, replacement, body)  # NOSONAR
                action = "updated"
            else:
                # 在文件末尾添加新配置项
                body = body.rstrip() + f'\n{item_name} {item_value};\n'
                action = "added"
        
        # 检查内容是否发生变化
        if body == original_content:
            return {
                "success": False,
                "error": f"配置项 '{item_name}' 未找到且无法自动添加"
            }
        
        # 写入新内容
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(body)
        
        # 获取旧值（如果有）
        old_value = None
        if action.startswith("updated"):
            old_match = re.search(rf'{item_name}\s+([^;\n]+)', original_content)  # NOSONAR
            if old_match:
                old_value = old_match.group(1).strip()
        
        return {
            "success": True,
            "action": action,
            "old_value": old_value
        }
        
    except Exception as e:
        logger.error(f"更新配置文件失败: {e}")
        return {
            "success": False,
            "error": f"更新配置文件失败: {e}"
        }

def save_config_files(config_files: List[str]) -> Dict:
    """
    备份配置文件
    
    Args:
        config_files: 配置文件路径列表
    
    Returns:
        dict: 备份结果
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"/tmp/nginx_config_backup_{timestamp}"  # NOSONAR
        os.makedirs(backup_dir, exist_ok=True)
        
        backed_up_files = []
        
        for config_file in config_files:
            if os.path.exists(config_file):
                backup_file = os.path.join(backup_dir, os.path.basename(config_file))
                shutil.copy2(config_file, backup_file)
                backed_up_files.append(backup_file)
        
        return {
            "success": True,
            "backup_path": backup_dir,
            "backed_up_files": backed_up_files,
            "message": f"配置文件已备份至: {backup_dir}"
        }
        
    except Exception as e:
        logger.error(f"备份配置文件失败: {e}")
        return {
            "success": False,
            "error": f"备份配置文件失败: {e}"
        }

def recover_config_files(config_files: List[str], backup_dir: str) -> Dict:
    """
    恢复配置文件
    
    Args:
        config_files: 配置文件路径列表
        backup_dir: 备份目录
    
    Returns:
        dict: 恢复结果
    """
    try:
        restored_files = []
        
        for config_file in config_files:
            backup_file = os.path.join(backup_dir, os.path.basename(config_file))
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, config_file)
                restored_files.append(config_file)
        
        return {
            "success": True,
            "restored_files": restored_files,
            "message": f"配置文件已从备份恢复: {backup_dir}"
        }
        
    except Exception as e:
        logger.error(f"恢复配置文件失败: {e}")
        return {
            "success": False,
            "error": f"恢复配置文件失败: {e}"
        }

def certify_nginx_config() -> Dict:
    """
    验证Nginx配置语法
    
    Returns:
        dict: 验证结果
    """
    try:
        cmd_result = execute_command(['nginx', '-t'], timeout=30)
        
        if cmd_result["success"]:
            output = cmd_result.get("output", "")
            if "syntax is ok" in output.lower() and "test is successful" in output.lower():
                return {
                    "success": True,
                    "message": "配置语法检查通过"
                }
            else:
                return {
                    "success": False,
                    "message": "配置语法检查完成，但输出异常",
                    "error": output
                }
        else:
            return {
                "success": False,
                "message": "配置语法检查失败",
                "error": cmd_result.get("error", "配置测试命令执行失败")
            }
        
    except Exception as e:
        logger.error(f"验证Nginx配置语法失败: {e}")
        return {
            "success": False,
            "message": f"配置语法检查失败: {e}",
            "error": str(e)
        }

def reload_nginx_config() -> Dict:
    """
    重载Nginx配置
    
    Returns:
        dict: 重载结果
    """
    try:
        cmd_result = execute_command(['nginx', '-s', 'reload'], timeout=60)
        
        if cmd_result["success"]:
            return {
                "success": True,
                "message": "配置重载成功"
            }
        else:
            return {
                "success": False,
                "message": "配置重载失败",
                "error": cmd_result.get("error", "重载命令执行失败")
            }
        
    except Exception as e:
        logger.error(f"重载Nginx配置失败: {e}")
        return {
            "success": False,
            "message": f"配置重载失败: {e}",
            "error": str(e)
        }

def fetch_config_item_recommendations(item_name: str) -> Dict:
    """
    获取配置项推荐值
    
    Args:
        item_name: 配置项名称
    
    Returns:
        dict: 推荐值信息
    """
    try:
        recommendations = {
            'worker_processes': {
                'description': '工作进程数',
                'recommended': 'auto',
                'explanation': '自动设置为CPU核心数，通常是最佳选择',
                'alternatives': ['2', '4', '8']
            },
            'worker_connections': {
                'description': '每个工作进程的最大连接数',
                'recommended': '1024',
                'explanation': '对于大多数应用足够，高并发场景可适当增加',
                'alternatives': ['2048', '4096', '8192']
            },
            'keepalive_timeout': {
                'description': '保持连接超时时间',
                'recommended': '65',
                'explanation': '平衡连接复用和资源占用',
                'alternatives': ['30', '60', '120']
            },
            'client_max_body_size': {
                'description': '客户端请求体最大大小',
                'recommended': '10m',
                'explanation': '适合大多数文件上传场景',
                'alternatives': ['1m', '50m', '100m']
            },
            'sendfile': {
                'description': '是否启用sendfile',
                'recommended': 'on',
                'explanation': '提高静态文件传输效率',
                'alternatives': ['off']
            }
        }
        
        recommendation = recommendations.get(item_name)
        if recommendation:
            return {
                "found": True,
                "item_name": item_name,
                "recommendation": recommendation
            }
        else:
            return {
                "found": False,
                "message": f"未找到配置项 '{item_name}' 的推荐值"
            }
        
    except Exception as e:
        logger.error(f"获取配置项推荐值失败: {e}")
        return {
            "found": False,
            "error": f"获取推荐值失败: {e}"
        }