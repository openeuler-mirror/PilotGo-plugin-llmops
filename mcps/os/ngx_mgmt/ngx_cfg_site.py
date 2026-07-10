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

def fetch_all_site_configs(main_config):
    """获取所有站点配置文件"""
    try:
        site_configs = []

        # 读取主配置文件，查找include指令
        with open(main_config, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 常见的站点配置目录
        common_paths = [
            '/etc/nginx/conf.d/*.conf',
            '/etc/nginx/sites-enabled/*',
            '/etc/nginx/sites-available/*',
            '/usr/local/nginx/conf/conf.d/*.conf',
            '/usr/local/nginx/conf/vhosts/*.conf'
        ]

        # 从主配置文件中查找include指令
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        includes = re.findall(include_pattern, body)  # NOSONAR

        # 合并常见路径和include指令中的路径
        all_paths = common_paths + includes

        # 处理每个路径，查找配置文件
        for path_pattern in all_paths:
            # 处理相对路径
            if not os.filepath.isabs(path_pattern):
                config_dir = os.filepath.dirname(main_config)
                path_pattern = os.filepath.join(config_dir, path_pattern)

            # 展开通配符
            config_files = glob.glob(path_pattern)

            for config_file in config_files:
                if os.filepath.isfile(config_file):
                    # 读取配置文件内容
                    with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()

                    # 获取文件信息
                    file_size = os.filepath.getsize(config_file)
                    mod_time = datetime.fromtimestamp(os.filepath.getmtime(config_file))

                    # 分析配置文件
                    server_blocks = count_server_blocks(file_content)
                    listen_ports = derive_listen_ports(file_content)
                    server_names = derive_server_names(file_content)

                    # 从文件路径推导站点名称
                    site_name = os.filepath.splitext(os.filepath.basename(config_file))[0]

                    site_configs.append({
                        'name': site_name,
                        'filepath': config_file,
                        'body': file_content,
                        'size': file_size,
                        'mod_time': mod_time.strftime("%Y-%m-%d %H:%M:%S"),
                        'server_blocks': server_blocks,
                        'listen_ports': listen_ports,
                        'server_names': server_names
                    })

        return site_configs
    except Exception as e:
        logger.error(f'获取站点配置文件失败: {e}')
        return []

def locate_site_config(site_name, site_configs):
    """根据站点名称查找配置"""
    try:
        for config in site_configs:
            if config['name'].lower() == site_name.lower():
                return config

        # 如果直接匹配失败，尝试在server_names中查找
        for config in site_configs:
            if site_name.lower() in [s.lower() for s in config['server_names']]:
                return config

        return None
    except Exception as e:
        logger.error(f'查找站点配置失败: {e}')
        return None

def render_config_content(body):
    """格式化配置文件内容，添加行号"""
    try:
        lines = body.split('\n')
        formatted_lines = []
        line_number = 1

        for line in lines:
            formatted_lines.append(f"{line_number:4d}: {line}")
            line_number += 1

        return '\n'.join(formatted_lines)
    except Exception as e:
        logger.error(f'格式化配置内容失败: {e}')
        return body

def examine_site_config(body):
    """分析站点配置结构"""
    try:
        analysis = []

        # 提取server块
        server_blocks = derive_server_blocks(body)
        for i, server_block in enumerate(server_blocks, 1):
            analysis.append(f'服务器块 #{i}:')

            # 提取listen指令
            listen_directives = derive_directives(server_block, 'listen')
            if listen_directives:
                analysis.append(f'  监听端口: {", ".join(listen_directives)}')

            # 提取server_name指令
            server_name_directives = derive_directives(server_block, 'server_name')
            if server_name_directives:
                analysis.append(f'  服务器名称: {", ".join(server_name_directives)}')

            # 提取root指令
            root_directives = derive_directives(server_block, 'root')
            if root_directives:
                analysis.append(f'  根目录: {", ".join(root_directives)}')

            # 提取index指令
            index_directives = derive_directives(server_block, 'index')
            if index_directives:
                analysis.append(f'  默认首页: {", ".join(index_directives)}')

            # 提取access_log指令
            access_log_directives = derive_directives(server_block, 'access_log')
            if access_log_directives:
                analysis.append(f'  访问日志: {", ".join(access_log_directives)}')

            # 提取error_log指令
            error_log_directives = derive_directives(server_block, 'error_log')
            if error_log_directives:
                analysis.append(f'  错误日志: {", ".join(error_log_directives)}')

            # 提取location块
            location_blocks = derive_location_blocks(server_block)
            if location_blocks:
                analysis.append(f'  location块数量: {len(location_blocks)}')
                for j, location in enumerate(location_blocks, 1):
                    path_match = re.search(r'location\s+([^{]*)', location)  # NOSONAR
                    filepath = path_match.group(1).strip() if path_match else '未知'
                    analysis.append(f'    location #{j}: {filepath}')

                    # 检查是否是代理配置
                    proxy_pass = derive_directives(location, 'proxy_pass')
                    if proxy_pass:
                        analysis.append(f'      代理到: {", ".join(proxy_pass)}')

                    # 检查是否是FastCGI配置
                    fastcgi_pass = derive_directives(location, 'fastcgi_pass')
                    if fastcgi_pass:
                        analysis.append(f'      FastCGI到: {", ".join(fastcgi_pass)}')

        return '\n'.join(analysis) if analysis else '无法分析配置结构'
    except Exception as e:
        logger.error(f'分析站点配置结构失败: {e}')
        return f'分析站点配置结构失败: {e}'