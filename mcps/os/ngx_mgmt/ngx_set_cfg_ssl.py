from datetime import datetime
from pathlib import Path
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_cfg_site import get_all_site_configs, find_site_config
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_ssl')

def adjust_nginx_ssl(site_name, action, **kwargs):
    """
    配置Nginx SSL证书和HTTPS设置

    参数:
        site_name: 站点名称（必需）
        action: 操作类型，可选值:
                'activate_https' - 启用HTTPS
                'deactivate_https' - 禁用HTTPS
                'update_cert' - 更新证书
                'set_protocols' - 设置加密协议
                'set_ciphers' - 设置加密套件
                'set_security' - 设置安全策略
        **kwargs: 其他参数，根据action不同而不同

    返回:
        str: 配置结果报告
    """
    try:
        # 验证操作类型
        valid_actions = ['activate_https', 'deactivate_https', 'update_cert',
                        'set_protocols', 'set_ciphers', 'set_security']
        if action not in valid_actions:
            return f'无效的操作类型: {action}。有效操作: {", ".join(valid_actions)}'

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
        original_content = site_config['body']

        # 备份原始配置
        backup_result = save_config_file(config_file_path, site_name)
        if not backup_result:
            return '配置备份失败，无法继续操作'

        # 根据操作类型执行相应配置
        if action == 'activate_https':
            output = activate_https(config_file_path, original_content, **kwargs)
        elif action == 'deactivate_https':
            output = deactivate_https(config_file_path, original_content)
        elif action == 'update_cert':
            output = modify_certificate(config_file_path, original_content, **kwargs)
        elif action == 'set_protocols':
            output = set_ssl_protocols(config_file_path, original_content, **kwargs)
        elif action == 'set_ciphers':
            output = set_ssl_ciphers(config_file_path, original_content, **kwargs)
        elif action == 'set_security':
            output = set_security_policy(config_file_path, original_content, **kwargs)

        # 验证配置语法
        validation_result = certify_nginx_config(config_file_path)
        if not validation_result['success']:
            # 配置验证失败，恢复备份
            restore_result = recover_config_backup(config_file_path, site_name)
            return f'配置语法验证失败，已自动恢复备份。错误信息: {validation_result["error"]}' if restore_result else f'配置语法验证失败且无法恢复备份: {validation_result["error"]}'
        # 重载配置
        reload_result = reload_nginx_config()
        if not reload_result['success']:
            return f'配置修改成功但重载失败: {reload_result["error"]}'

        # 生成配置报告
        report = produce_ssl_config_report(site_name, action, output, **kwargs)
        return report

    except Exception as e:
        logger.error(f'配置Nginx SSL失败: {e}')
        return f'配置Nginx SSL失败: {e}'

def activate_https(config_file_path, original_content, cert_path=None, key_path=None,
                redirect_http=True, http2_enabled=True, protocols='TLSv1.2 TLSv1.3',
                ciphers=None, security_headers=True):
    """启用 HTTPS 配置"""
    try:
        # 安全验证：验证 config_file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_file_path, allow_absolute=True)
        if not valid:
            logger.error(f"activate_https: config_file_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'配置文件路径不安全：{error_msg}'}

        # 安全验证：验证 cert_path 路径参数（如果提供，允许绝对路径）
        if cert_path is not None:
            valid, error_msg = validate_path_param(cert_path, allow_absolute=True)
            if not valid:
                logger.error(f"activate_https: cert_path 路径验证失败：{error_msg}")
                return {'success': False, 'message': f'证书文件路径不安全：{error_msg}'}

        # 安全验证：验证 key_path 路径参数（如果提供，允许绝对路径）
        if key_path is not None:
            valid, error_msg = validate_path_param(key_path, allow_absolute=True)
            if not valid:
                logger.error(f"activate_https: key_path 路径验证失败：{error_msg}")
                return {'success': False, 'message': f'私钥文件路径不安全：{error_msg}'}

        body = Path(config_file_path).read_text(encoding='utf-8')

        # 检查是否已启用HTTPS
        if 'ssl_certificate' in body and 'ssl_certificate_key' in body:
            return {'success': False, 'message': '该站点已启用HTTPS'}

        # 读取原始配置内容
        lines = original_content.split('\n')
        modified_lines = []
        server_block_found = False
        server_block_lines = []
        brace_count = 0
        server_start = -1

        # 查找server块
        for i, line in enumerate(lines):
            if re.search(r'listen\s+80;', line.strip()):  # NOSONAR
                # 修改80端口监听，添加重定向
                if redirect_http:
                    modified_line = f"    listen 80;\n    return 301 https://$host$request_uri;"
                    modified_lines.append(modified_line)
                else:
                    modified_lines.append(line)
            elif re.search(r'server\s*\{', line.strip()):  # NOSONAR
                server_block_found = True
                server_start = i
                brace_count = 1
                modified_lines.append(line)
            elif server_block_found:
                if '{' in line:
                    brace_count += 1
                if '}' in line:
                    brace_count -= 1
                    if brace_count == 0:
                        # 在server块结束前插入HTTPS配置
                        ssl_config = produce_ssl_config(cert_path, key_path, http2_enabled,
                                                       protocols, ciphers, security_headers)
                        modified_lines.extend(ssl_config)
                        modified_lines.append(line)
                        server_block_found = False
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)

        # 如果没有找到server块，创建新的HTTPS server块
        if not server_block_found:
            ssl_config = produce_ssl_config(cert_path, key_path, http2_enabled,
                                           protocols, ciphers, security_headers)
            modified_lines.extend(ssl_config)

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(modified_lines))

        return {'success': True, 'message': 'HTTPS配置已启用'}

    except Exception as e:
        logger.error(f'启用HTTPS失败: {e}')
        return {'success': False, 'message': f'启用HTTPS失败: {e}'}

def deactivate_https(config_file_path, original_content):
    """禁用HTTPS配置"""
    try:
        body = Path(config_file_path).read_text(encoding='utf-8')

        # 检查是否已禁用HTTPS
        if 'ssl_certificate' not in body and 'ssl_certificate_key' not in body:
            return {'success': False, 'message': '该站点未启用HTTPS'}

        # 移除SSL相关配置
        ssl_directives = [
            r'ssl_certificate\s+[^;]+;',
            r'ssl_certificate_key\s+[^;]+;',
            r'ssl_protocols\s+[^;]+;',
            r'ssl_ciphers\s+[^;]+;',
            r'ssl_prefer_server_ciphers\s+[^;]+;',
            r'ssl_session_cache\s+[^;]+;',
            r'ssl_session_timeout\s+[^;]+;',
            r'add_header\s+Strict-Transport-Security\s+[^;]+;'
        ]

        modified_content = body
        for directive in ssl_directives:
            modified_content = re.sub(directive, '', modified_content)  # NOSONAR

        # 修改监听端口
        modified_content = re.sub(r'listen\s+443\s+ssl;', 'listen 80;', modified_content)  # NOSONAR
        modified_content = re.sub(r'listen\s+\[::\]:443\s+ssl;', 'listen [::]:80;', modified_content)  # NOSONAR

        # 移除HTTP重定向
        modified_content = re.sub(r'listen\s+80;\s*return\s+301\s+https://\$host\$request_uri;',  # NOSONAR
                                'listen 80;', modified_content)

        # 清理空行
        modified_content = re.sub(r'\n\s*\n', '\n', modified_content)  # NOSONAR

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        return {'success': True, 'message': 'HTTPS配置已禁用'}

    except Exception as e:
        logger.error(f'禁用HTTPS失败: {e}')
        return {'success': False, 'message': f'禁用HTTPS失败: {e}'}

def modify_certificate(config_file_path, original_content, cert_path, key_path):
    """更新 SSL 证书"""
    try:
        # 安全验证：验证 config_file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_file_path, allow_absolute=True)
        if not valid:
            logger.error(f"modify_certificate: config_file_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'配置文件路径不安全：{error_msg}'}

        # 安全验证：验证 cert_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cert_path, allow_absolute=True)
        if not valid:
            logger.error(f"modify_certificate: cert_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'证书文件路径不安全：{error_msg}'}

        # 安全验证：验证 key_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(key_path, allow_absolute=True)
        if not valid:
            logger.error(f"modify_certificate: key_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'私钥文件路径不安全：{error_msg}'}

        # 验证证书文件是否存在
        if not os.path.exists(cert_path):
            return {'success': False, 'message': f'证书文件不存在：{cert_path}'}
        if not os.path.exists(key_path):
            return {'success': False, 'message': f'私钥文件不存在：{key_path}'}

        # 验证证书格式
        cert_valid = certify_certificate(cert_path)
        key_valid = certify_private_key(key_path)

        if not cert_valid:
            return {'success': False, 'message': '证书文件格式无效'}
        if not key_valid:
            return {'success': False, 'message': '私钥文件格式无效'}

        body = Path(config_file_path).read_text(encoding='utf-8')

        # 更新证书路径
        updated_content = re.sub(r'ssl_certificate\s+[^;]+;',  # NOSONAR
                               f'ssl_certificate {cert_path};', body)
        updated_content = re.sub(r'ssl_certificate_key\s+[^;]+;',  # NOSONAR
                               f'ssl_certificate_key {key_path};', updated_content)

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return {'success': True, 'message': 'SSL证书已更新'}

    except Exception as e:
        logger.error(f'更新证书失败: {e}')
        return {'success': False, 'message': f'更新证书失败: {e}'}

def set_ssl_protocols(config_file_path, original_content, protocols='TLSv1.2 TLSv1.3'):
    """设置 SSL 协议版本"""
    try:
        # 安全验证：验证 config_file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_file_path, allow_absolute=True)
        if not valid:
            logger.error(f"set_ssl_protocols: config_file_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'配置文件路径不安全：{error_msg}'}

        valid_protocols = ['TLSv1', 'TLSv1.1', 'TLSv1.2', 'TLSv1.3']
        protocols_list = protocols.split()

        for protocol in protocols_list:
            if protocol not in valid_protocols:
                return {'success': False, 'message': f'无效的SSL协议: {protocol}'}

        body = Path(config_file_path).read_text(encoding='utf-8')

        # 更新或添加ssl_protocols指令
        if 'ssl_protocols' in body:
            updated_content = re.sub(r'ssl_protocols\s+[^;]+;',  # NOSONAR
                                   f'ssl_protocols {protocols};', body)
        else:
            # 在server块内添加ssl_protocols指令
            updated_content = body.replace('listen 443 ssl;',
                                            f'listen 443 ssl;\n    ssl_protocols {protocols};')

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return {'success': True, 'message': f'SSL协议已设置为: {protocols}'}

    except Exception as e:
        logger.error(f'设置SSL协议失败: {e}')
        return {'success': False, 'message': f'设置SSL协议失败: {e}'}

def set_ssl_ciphers(config_file_path, original_content, ciphers=None):
    """设置 SSL 加密套件"""
    try:
        # 安全验证：验证 config_file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_file_path, allow_absolute=True)
        if not valid:
            logger.error(f"set_ssl_ciphers: config_file_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'配置文件路径不安全：{error_msg}'}

        if ciphers is None:
            # 使用安全的默认加密套件
            ciphers = 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384'

        body = Path(config_file_path).read_text(encoding='utf-8')

        # 更新或添加ssl_ciphers指令
        if 'ssl_ciphers' in body:
            updated_content = re.sub(r'ssl_ciphers\s+[^;]+;',  # NOSONAR
                                   f'ssl_ciphers {ciphers};', body)
        else:
            # 在server块内添加ssl_ciphers指令
            updated_content = body.replace('listen 443 ssl;',
                                            f'listen 443 ssl;\n    ssl_ciphers {ciphers};')

        # 添加ssl_prefer_server_ciphers指令
        if 'ssl_prefer_server_ciphers' not in updated_content:
            updated_content = updated_content.replace('ssl_ciphers',
                                                    'ssl_ciphers\n    ssl_prefer_server_ciphers on;')

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return {'success': True, 'message': f'SSL加密套件已设置'}

    except Exception as e:
        logger.error(f'设置SSL加密套件失败: {e}')
        return {'success': False, 'message': f'设置SSL加密套件失败: {e}'}

def set_security_policy(config_file_path, original_content, hsts_max_age=31536000,
                       hsts_include_subdomains=True, hsts_preload=False,
                       enable_ocsp_stapling=True, enable_dhparam=True):
    """设置安全策略"""
    try:
        # 安全验证：验证 config_file_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(config_file_path, allow_absolute=True)
        if not valid:
            logger.error(f"set_security_policy: config_file_path 路径验证失败：{error_msg}")
            return {'success': False, 'message': f'配置文件路径不安全：{error_msg}'}

        body = Path(config_file_path).read_text(encoding='utf-8')

        security_directives = []

        # HSTS头设置
        hsts_directive = f'max-age={hsts_max_age}'
        if hsts_include_subdomains:
            hsts_directive += '; includeSubDomains'
        if hsts_preload:
            hsts_directive += '; preload'

        security_directives.append(f'add_header Strict-Transport-Security "{hsts_directive}";')

        # 其他安全头
        security_directives.extend([
            'add_header X-Frame-Options "SAMEORIGIN";',
            'add_header X-Content-Type-Options "nosniff";',
            'add_header X-XSS-Protection "1; mode=block";',
            'add_header Referrer-Policy "strict-origin-when-cross-origin";'
        ])

        # OCSP装订
        if enable_ocsp_stapling:
            security_directives.extend([
                'ssl_stapling on;',
                'ssl_stapling_verify on;',
                'resolver 8.8.8.8 8.8.4.4 valid=300s;',
                'resolver_timeout 5s;'
            ])

        # 写入安全配置
        security_config = '\n    '.join(security_directives)
        updated_content = body

        # 在server块内添加安全配置
        if 'listen 443 ssl;' in updated_content:
            updated_content = updated_content.replace('listen 443 ssl;',
                                                    f'listen 443 ssl;\n    {security_config}')
        else:
            # 添加到server块末尾
            updated_content = updated_content.replace('}', f'    {security_config}\n}}')

        # 写入修改后的配置
        with open(config_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return {'success': True, 'message': '安全策略已设置'}

    except Exception as e:
        logger.error(f'设置安全策略失败: {e}')
        return {'success': False, 'message': f'设置安全策略失败: {e}'}