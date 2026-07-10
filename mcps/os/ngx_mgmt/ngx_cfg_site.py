from datetime import datetime
import glob
import logging
import os
import re
import subprocess

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_site')

def fetch_nginx_config_site(site_name=None):
    """
    获取Nginx站点配置文件内容、所有站点配置列表及路径

    参数:
        site_name: 可选，指定要查看的站点名称，如果不指定则显示所有站点列表

    返回:
        str: 格式化的站点配置信息
    """
    try:
        output = []

        # 获取nginx配置信息
        cfg_state = get_nginx_config_info()
        main_config = cfg_state.get('config_file', '')

        if not main_config or main_config == 'Unknown' or main_config == '获取失败':
            output.append('无法获取Nginx主配置文件路径')
            return '\n'.join(output)

        # 获取所有站点配置文件路径
        site_configs = fetch_all_site_configs(main_config)

        if not site_configs:
            output.append('未找到任何站点配置文件')
            return '\n'.join(output)

        # 如果指定了站点名称，只显示该站点配置
        if site_name:
            site_config = locate_site_config(site_name, site_configs)
            if site_config:
                output.append(f'=== 站点配置: {site_name} ===')
                output.append(f'配置文件路径: {site_config["filepath"]}')
                output.append(f'文件大小: {site_config["size"]} 字节')
                output.append(f'最后修改时间: {site_config["mod_time"]}')

                # 显示配置文件内容
                output.append('\n--- 配置文件内容 ---')
                output.append(render_config_content(site_config["body"]))

                # 分析配置结构
                output.append('\n--- 配置结构分析 ---')
                output.append(examine_site_config(site_config["body"]))
            else:
                output.append(f'未找到名为 "{site_name}" 的站点配置')
                output.append('\n可用的站点配置列表:')
                for config in site_configs:
                    output.append(f"  - {config['name']}: {config['filepath']}")
        else:
            # 显示所有站点配置列表
            output.append('=== Nginx站点配置列表 ===')
            output.append(f'主配置文件: {main_config}')
            output.append(f'找到 {len(site_configs)} 个站点配置文件\n')

            for i, config in enumerate(site_configs, 1):
                output.append(f'{i}. 站点名称: {config["name"]}')
                output.append(f'   配置文件路径: {config["filepath"]}')
                output.append(f'   文件大小: {config["size"]} 字节')
                output.append(f'   最后修改时间: {config["mod_time"]}')
                output.append(f'   服务器块数量: {config["server_blocks"]}')
                output.append(f'   监听端口: {", ".join(config["listen_ports"])}')
                output.append(f'   服务器名称: {", ".join(config["server_names"])}')
                output.append('')

        output.append('======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx站点配置失败: {e}')
        return f'获取Nginx站点配置失败: {e}'