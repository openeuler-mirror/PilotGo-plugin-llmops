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