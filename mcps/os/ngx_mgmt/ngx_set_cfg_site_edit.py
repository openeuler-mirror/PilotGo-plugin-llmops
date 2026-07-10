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

def certify_modify_parameters(site_name, port, root_path, server_names,
                             proxy_target, enable_ssl, enable_php):
    """验证修改参数"""
    try:
        # 验证站点名称
        if not site_name or not isinstance(site_name, str):
            return '站点名称必须为有效的字符串'

        # 使用通用验证函数进行标识符验证
        is_valid, error_msg = validate_identifier_param(site_name, allow_slash=False)
        if not is_valid:
            return f'站点名称格式不合法：{error_msg}'

        # 验证端口
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                return '端口号必须是 1-65535 之间的整数'

        # 验证根路径（如果提供）
        if root_path is not None:
            if not isinstance(root_path, str):
                return '根路径必须为有效的字符串'
            # 安全验证：验证 root_path 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(root_path, allow_absolute=True)
            if not valid:
                return f'根路径不安全：{error_msg}'

        # 验证服务器名称
        if server_names is not None:
            if isinstance(server_names, str):
                server_names = [server_names]
            elif not isinstance(server_names, list):
                return '服务器名称必须为字符串或字符串列表'

        # 验证代理目标（如果提供）
        if proxy_target is not None:
            if not isinstance(proxy_target, str):
                return '代理目标地址必须为有效的字符串'
            # 安全验证：验证 proxy_target 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(proxy_target, allow_absolute=True)
            if not valid:
                return f'代理目标地址不安全：{error_msg}'

        # 验证布尔参数
        if enable_ssl is not None and not isinstance(enable_ssl, bool):
            return 'enable_ssl 参数必须为布尔值'

        if enable_php is not None and not isinstance(enable_php, bool):
            return 'enable_php 参数必须为布尔值'

        return None

    except Exception as e:
        logger.error(f'验证修改参数失败: {e}')
        return f'参数验证失败: {e}'

def modify_config_content(original_content, port, root_path, server_names,
                        proxy_target, enable_ssl, enable_php):
    """修改配置内容"""
    try:
        lines = original_content.split('\n')
        modified_lines = []
        in_server_block = False
        server_block_start = -1
        server_block_end = -1

        # 查找server块的开始和结束位置
        brace_count = 0
        for i, line in enumerate(lines):
            modified_lines.append(line)

            # 检测server块开始
            if re.search(r'server\s*\{', line.strip()):  # NOSONAR
                if not in_server_block:
                    in_server_block = True
                    server_block_start = i
                    brace_count = 1
                else:
                    brace_count += 1
            # 检测大括号
            elif in_server_block:
                if '{' in line:
                    brace_count += 1
                if '}' in line:
                    brace_count -= 1
                    if brace_count == 0:
                        server_block_end = i
                        break

        # 如果没有找到完整的server块，返回原始内容
        if server_block_start == -1 or server_block_end == -1:
            logger.warning('未找到完整的server块，无法修改配置')
            return original_content

        # 提取server块内容进行修改
        server_block_lines = lines[server_block_start:server_block_end + 1]
        modified_server_block = modify_server_block(server_block_lines, port, root_path,
                                                  server_names, proxy_target,
                                                  enable_ssl, enable_php)

        # 替换修改后的server块
        modified_lines = lines[:server_block_start] + modified_server_block + lines[server_block_end + 1:]

        return '\n'.join(modified_lines)

    except Exception as e:
        logger.error(f'修改配置内容失败: {e}')
        return original_content

def modify_server_block(server_block_lines, port, root_path, server_names,
                       proxy_target, enable_ssl, enable_php):
    """修改server块内容"""
    try:
        modified_block = []
        modified_directives = set()

        for line in server_block_lines:
            original_line = line
            line_stripped = line.strip()

            # 修改监听端口
            if port is not None and re.match(r'^\s*listen\s+', line_stripped):  # NOSONAR
                if 'ssl' in line_stripped and enable_ssl is not False:
                    # 保持SSL配置，只修改端口号
                    new_line = re.sub(r'listen\s+[^;]+;',  # NOSONAR
                                    f'listen {port} ssl http2;', line)
                else:
                    new_line = re.sub(r'listen\s+[^;]+;', f'listen {port};', line)  # NOSONAR

                if new_line != original_line:
                    line = new_line
                    modified_directives.add('listen')

            # 修改服务器名称
            elif server_names is not None and re.match(r'^\s*server_name\s+', line_stripped):  # NOSONAR
                names_str = ' '.join(server_names) if isinstance(server_names, list) else server_names
                new_line = re.sub(r'server_name\s+[^;]+;',  # NOSONAR
                                f'server_name {names_str};', line)

                if new_line != original_line:
                    line = new_line
                    modified_directives.add('server_name')

            # 修改根路径
            elif root_path is not None and re.match(r'^\s*root\s+', line_stripped):  # NOSONAR
                new_line = re.sub(r'root\s+[^;]+;', f'root {root_path};', line)  # NOSONAR

                if new_line != original_line:
                    line = new_line
                    modified_directives.add('root')

            # 修改代理目标
            elif proxy_target is not None and re.match(r'^\s*proxy_pass\s+', line_stripped):  # NOSONAR
                new_line = re.sub(r'proxy_pass\s+[^;]+;',  # NOSONAR
                                f'proxy_pass {proxy_target};', line)

                if new_line != original_line:
                    line = new_line
                    modified_directives.add('proxy_pass')

            # 启用/禁用SSL
            elif enable_ssl is not None:
                if enable_ssl and re.match(r'^\s*listen\s+', line_stripped) and 'ssl' not in line_stripped:  # NOSONAR
                    # 添加SSL支持
                    line = line.replace(';', ' ssl http2;')
                    modified_directives.add('ssl')
                elif not enable_ssl and 'ssl' in line_stripped:
                    # 移除SSL支持
                    line = re.sub(r'\s+ssl\s+http2', '', line)  # NOSONAR
                    modified_directives.add('ssl')

            # 启用/禁用PHP支持
            elif enable_php is not None and re.search(r'location\s+~\s*\\\.php', line_stripped):  # NOSONAR
                # 这里需要更复杂的逻辑来处理PHP配置的启用/禁用
                # 暂时跳过，需要更完整的实现
                pass

            modified_block.append(line)

        # 添加缺失的配置项
        modified_block = add_missing_directives(modified_block, port, root_path,
                                              server_names, proxy_target,
                                              enable_ssl, modified_directives)

        return modified_block

    except Exception as e:
        logger.error(f'修改server块失败: {e}')
        return server_block_lines