from datetime import datetime
from pathlib import Path
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_site_create')

def build_nginx_site_config(site_name, port=80, root_path="/var/www/html",
                           server_names=None, config_type="basic",
                           enable_ssl=False, enable_php=False,
                           enable_proxy=False, proxy_target=None,
                           config_dir=None):
    """
    创建Nginx新站点配置，支持基础配置快速生成

    参数:
        site_name: 站点名称（必需）
        port: 监听端口，默认80
        root_path: 网站根路径，默认/var/www/html
        server_names: 服务器名称列表（域名），默认使用站点名称
        config_type: 配置类型，支持"basic"/"php"/"proxy"/"static"
        enable_ssl: 是否启用SSL，默认False
        enable_php: 是否启用PHP支持，默认False
        enable_proxy: 是否启用代理，默认False
        proxy_target: 代理目标地址
        config_dir: 配置文件目录，默认自动检测

    返回:
        str: 创建结果报告
    """
    try:
        output = []

        # 参数验证
        validation_result = certify_create_parameters(site_name, port, root_path,
                                                     server_names, config_type,
                                                     enable_ssl, enable_php,
                                                     enable_proxy, proxy_target)
        if validation_result:
            return validation_result

        # 获取Nginx配置信息
        cfg_state = get_nginx_config_info()
        main_config = cfg_state.get('config_file', '')

        if not main_config or main_config == 'Unknown' or main_config == '获取失败':
            return '无法获取Nginx主配置文件路径，请检查Nginx是否已安装'

        # 确定配置文件目录
        config_dir = determine_config_dir(main_config, config_dir)
        if not config_dir:
            return '无法确定配置文件目录，请手动指定config_dir参数'

        # 生成配置文件内容
        config_content = produce_site_config(site_name, port, root_path,
                                            server_names, config_type,
                                            enable_ssl, enable_php,
                                            enable_proxy, proxy_target)

        # 生成配置文件路径
        config_file_path = produce_config_file_path(config_dir, site_name)

        # 检查文件是否已存在
        if os.path.exists(config_file_path):
            return f'配置文件已存在: {config_file_path}，请先删除或使用不同的站点名称'

        # 创建配置文件
        create_result = build_config_file(config_file_path, config_content)
        if not create_result:
            return f'创建配置文件失败: {config_file_path}'

        # 生成报告
        report = produce_creation_report(site_name, port, root_path, server_names,
                                        config_type, enable_ssl, enable_php,
                                        enable_proxy, proxy_target, config_file_path)

        return report

    except Exception as e:
        logger.error(f'创建Nginx站点配置失败: {str(e)}')
        return f'创建Nginx站点配置失败: {str(e)}'

def certify_create_parameters(site_name, port, root_path, server_names,
                             config_type, enable_ssl, enable_php,
                             enable_proxy, proxy_target):
    """验证创建参数"""
    try:
        # 验证站点名称
        if not site_name or not re.match(r'^[a-zA-Z0-9_-]+$', site_name):  # NOSONAR
            return '站点名称只能包含字母、数字、下划线和连字符'

        # 验证端口
        if not isinstance(port, int) or port < 1 or port > 65535:
            return '端口号必须是1-65535之间的整数'

        # 验证根路径
        if not root_path or not isinstance(root_path, str):
            return '根路径必须为有效的字符串'

        # 验证配置类型
        valid_config_types = ["basic", "php", "proxy", "static"]
        if config_type not in valid_config_types:
            return f'配置类型必须是: {", ".join(valid_config_types)}'

        # 验证代理配置
        if enable_proxy and not proxy_target:
            return '启用代理时，必须指定代理目标地址'

        # 服务器名称处理
        if server_names is None:
            server_names = [site_name]
        elif isinstance(server_names, str):
            server_names = [server_names]

        return None

    except Exception as e:
        logger.error(f'验证参数失败: {str(e)}')
        return f'参数验证失败: {str(e)}'

def determine_config_dir(main_config, user_config_dir):
    """确定配置文件目录"""
    try:
        # 如果用户指定了目录，直接使用
        if user_config_dir:
            if os.path.isdir(user_config_dir):
                return user_config_dir
            logger.warning(f'用户指定的目录不存在: {user_config_dir}')

        # 常见的站点配置目录
        common_dirs = [
            '/etc/nginx/conf.d',
            '/etc/nginx/sites-available',
            '/usr/local/nginx/conf/conf.d',
            '/usr/local/nginx/conf/vhosts'
        ]

        # 检查主配置文件所在目录的兄弟目录
        main_dir = os.path.dirname(main_config)
        sibling_dirs = [
            os.path.join(main_dir, 'conf.d'),
            os.path.join(main_dir, 'sites-available'),
            os.path.join(main_dir, 'vhosts')
        ]

        # 合并所有可能的目录
        all_dirs = common_dirs + sibling_dirs

        # 查找存在的目录
        for dir_path in all_dirs:
            if os.path.isdir(dir_path):
                return dir_path

        # 如果都找不到，使用主配置文件所在目录
        return main_dir

    except Exception as e:
        logger.error(f'确定配置文件目录失败: {str(e)}')
        return None