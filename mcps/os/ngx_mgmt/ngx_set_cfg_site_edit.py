from datetime import datetime
from pathlib import Path
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_cfg_site import get_all_site_configs, find_site_config
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_site_modify')

def modify_nginx_site_config(site_name, port=None, root_path=None,
                           server_names=None, proxy_target=None,
                           enable_ssl=None, enable_php=None,
                           backup_before_modify=True, reload_after_modify=True):
    """
    修改指定Nginx站点配置（如端口、根路径、反向代理地址）

    参数:
        site_name: 站点名称（必需）
        port: 新的监听端口，None表示不修改
        root_path: 新的网站根路径，None表示不修改
        server_names: 新的服务器名称列表，None表示不修改
        proxy_target: 新的代理目标地址，None表示不修改
        enable_ssl: 是否启用SSL，None表示不修改
        enable_php: 是否启用PHP支持，None表示不修改
        backup_before_modify: 修改前是否备份，默认True
        reload_after_modify: 修改后是否重载配置，默认True

    返回:
        str: 修改结果报告
    """
    try:
        output = []

        # 参数验证
        validation_result = certify_modify_parameters(site_name, port, root_path,
                                                     server_names, proxy_target,
                                                     enable_ssl, enable_php)
        if validation_result:
            return validation_result

        # 获取Nginx配置信息
        cfg_state = get_nginx_config_info()
        main_config = cfg_state.get('config_file', '')

        if not main_config or main_config == 'Unknown' or main_config == '获取失败':
            return '无法获取Nginx主配置文件路径，请检查Nginx是否已安装'

        # 查找站点配置
        site_configs = get_all_site_configs(main_config)
        site_config = find_site_config(site_name, site_configs)

        if not site_config:
            available_sites = [config['name'] for config in site_configs]
            return f'未找到名为 "{site_name}" 的站点配置。可用站点: {", ".join(available_sites)}'

        config_file_path = site_config['path']
        original_content = site_config['content']

        # 备份原始配置
        if backup_before_modify:
            backup_result = save_config_file(config_file_path)
            if backup_result:
                output.append(f'配置备份成功: {backup_result}')
            else:
                output.append('配置备份失败，但将继续修改')

        # 修改配置内容
        modified_content = modify_config_content(original_content, port, root_path,
                                               server_names, proxy_target,
                                               enable_ssl, enable_php)

        # 检查是否有实际修改
        if modified_content == original_content:
            return '未检测到需要修改的配置项，配置内容保持不变'

        # 写入修改后的配置
        write_result = store_modified_config(config_file_path, modified_content)
        if not write_result:
            return f'写入修改后的配置失败: {config_file_path}'

        # 验证配置语法
        validation_result = certify_nginx_config(config_file_path)
        if not validation_result['success']:
            # 配置验证失败，恢复备份
            restore_result = recover_config_backup(config_file_path)
            if restore_result:
                output.append('配置语法验证失败，已自动恢复备份')
                output.append(f'错误信息: {validation_result["error"]}')
                return '\n'.join(output)
            else:
                return f'配置语法验证失败且无法恢复备份: {validation_result["error"]}'

        # 重载配置
        if reload_after_modify:
            reload_result = reload_nginx_config()
            if reload_result['success']:
                output.append('Nginx配置重载成功')
            else:
                output.append(f'Nginx配置重载失败: {reload_result["error"]}')

        # 生成修改报告
        report = produce_modification_report(site_name, config_file_path,
                                            original_content, modified_content,
                                            port, root_path, server_names,
                                            proxy_target, enable_ssl, enable_php)

        output.append(report)
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'修改Nginx站点配置失败: {e}')
        return f'修改Nginx站点配置失败: {e}'