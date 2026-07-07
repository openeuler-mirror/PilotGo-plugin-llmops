import glob
import glob
import logging
import os
import re
import socket
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_port')

def fetch_nginx_base_port():
    """
    获取Nginx监听的所有TCP/UDP端口、绑定IP以及端口对应的站点配置的MCP工具

    返回:
        格式化的Nginx端口监听和站点配置信息字符串，包含：
        - Nginx监听端口列表
        - 绑定IP地址信息
        - 端口对应的站点配置
        - 虚拟主机配置详情
        - SSL/TLS配置信息
    """
    try:
        output = []
        output.append('=== Nginx端口监听和站点配置信息 ===')

        # 检查Nginx是否安装
        nginx_info = check_nginx_installation()
        if not nginx_info['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_info['suggestion']}")
            output.append('====================================')
            return '\n'.join(output)

        output.append(f"Nginx状态: 已安装")
        output.append(f"安装路径: {nginx_info['path']}")

        # 获取配置信息
        cfg_state = get_nginx_config_info()
        config_file = cfg_state['config_file']

        if config_file == 'Unknown' or not os.path.exists(config_file):
            output.append(f"配置文件: 未找到")
            output.append('====================================')
            return '\n'.join(output)

        output.append(f"主配置文件: {config_file}")
        output.append(f"配置测试: {cfg_state['config_test']}")

        # 获取Nginx监听端口和站点配置
        port_info = fetch_nginx_listen_ports(config_file)
        site_configs = fetch_nginx_site_configs(config_file)

        # 显示监听端口信息
        output.append(f"\n=== 监听端口信息 ===")
        if port_info['listen_ports']:
            output.append(f"总监听端口数: {len(port_info['listen_ports'])}")

            # 按端口类型分组显示
            http_ports = [p for p in port_info['listen_ports'] if p['port'] in ['80', '8080', '8000']]
            https_ports = [p for p in port_info['listen_ports'] if p['port'] in ['443', '8443']]
            other_ports = [p for p in port_info['listen_ports'] if p['port'] not in ['80', '8080', '8000', '443', '8443']]

            if http_ports:
                output.append(f"\nHTTP端口:")
                for port in http_ports:
                    output.append(f"  - {port['port']} ({port['ip']}) - {port['server_name']}")

            if https_ports:
                output.append(f"\nHTTPS端口:")
                for port in https_ports:
                    output.append(f"  - {port['port']} ({port['ip']}) - {port['server_name']}")
                    if port.get('ssl_info'):
                        output.append(f"    SSL: {port['ssl_info']}")

            if other_ports:
                output.append(f"\n其他端口:")
                for port in other_ports:
                    output.append(f"  - {port['port']} ({port['ip']}) - {port['server_name']}")
        else:
            output.append("未找到监听端口配置")

        # 显示站点配置
        output.append(f"\n=== 虚拟主机配置 ===")
        if site_configs:
            output.append(f"虚拟主机数量: {len(site_configs)}")

            for i, site in enumerate(site_configs, 1):
                output.append(f"\n虚拟主机 {i}:")
                output.append(f"  域名: {site.get('server_name', '默认')}")
                output.append(f"  监听端口: {', '.join(site.get('listen_ports', []))}")
                output.append(f"  根目录: {site.get('root', '未配置')}")
                output.append(f"  索引文件: {site.get('index', '未配置')}")

                if site.get('ssl_enabled'):
                    output.append(f"  SSL: 已启用")
                    if site.get('ssl_cert'):
                        output.append(f"  SSL证书: {site['ssl_cert']}")
                    if site.get('ssl_key'):
                        output.append(f"  SSL密钥: {site['ssl_key']}")

                if site.get('locations'):
                    output.append(f"  位置配置:")
                    for location in site['locations'][:3]:  # 只显示前3个location
                        output.append(f"    - {location['path']} -> {location.get('proxy_pass', location.get('root', '本地目录'))}")
                    if len(site['locations']) > 3:
                        output.append(f"    ... 还有 {len(site['locations']) - 3} 个 location ...")
        else:
            output.append("未找到虚拟主机配置")

        # 显示系统端口监听状态
        output.append(f"\n=== 系统端口监听状态 ===")
        system_ports = fetch_system_port_status()
        if system_ports:
            nginx_ports = [p for p in system_ports if 'nginx' in p.get('process', '').lower()]
            if nginx_ports:
                output.append(f"Nginx进程监听端口:")
                for port in nginx_ports:
                    output.append(f"  - {port['protocol']} {port['local_addr']} (PID: {port.get('pid', '未知')})")
            else:
                output.append("未找到Nginx进程监听的端口")
        else:
            output.append("无法获取系统端口监听信息")

        # 端口冲突检查
        output.append(f"\n=== 端口冲突检查 ===")
        conflicts = verify_port_conflicts(port_info['listen_ports'], system_ports)
        if conflicts:
            output.append(f"发现端口冲突:")
            for conflict in conflicts:
                output.append(f"  - 端口 {conflict['port']}: Nginx({conflict['nginx_process']}) vs {conflict['other_process']}")
        else:
            output.append("未发现端口冲突")

        output.append('\n====================================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx端口和站点配置信息失败: {e}')
        return f'获取Nginx端口和站点配置信息失败: {e}'

def fetch_nginx_listen_ports(config_file):
    """
    获取Nginx监听端口配置

    参数:
        config_file: Nginx主配置文件路径

    返回:
        dict: 包含监听端口列表和相关信息的字典
    """
    try:
        listen_ports = []

        # 读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()

        # 包含其他配置文件
        include_files = re.findall(r'include\s+([^;]+);', body)  # NOSONAR
        all_content = body

        for include_pattern in include_files:
            # 处理通配符
            if '*' in include_pattern:
                include_pattern = include_pattern.strip()
                if not include_pattern.startswith('/'):
                    # 相对路径，基于配置文件目录
                    config_dir = os.path.dirname(config_file)
                    include_pattern = os.path.join(config_dir, include_pattern)

                for include_file in glob.glob(include_pattern):
                    if os.path.exists(include_file):
                        try:
                            with open(include_file, 'r', encoding='utf-8') as f:
                                all_content += '\n' + f.read()
                        except Exception as e:
                            logger.warning(f'读取包含文件失败 {include_file}: {e}')

        # 查找server块
        server_blocks = re.findall(r'server\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', all_content, re.DOTALL)  # NOSONAR

        for server_block in server_blocks:
            # 在每个server块中查找listen指令
            listen_matches = re.findall(r'listen\s+([^;]+);', server_block)  # NOSONAR
            server_name_matches = re.findall(r'server_name\s+([^;]+);', server_block)  # NOSONAR

            server_names = []
            for name_match in server_name_matches:
                server_names.extend(name_match.strip().split())

            if not server_names:
                server_names = ['默认主机']

            # 查找SSL配置
            ssl_enabled = 'ssl' in server_block.lower()
            ssl_cert_match = re.search(r'ssl_certificate\s+([^;]+);', server_block)  # NOSONAR
            ssl_key_match = re.search(r'ssl_certificate_key\s+([^;]+);', server_block)  # NOSONAR

            for listen_match in listen_matches:
                listen_config = listen_match.strip()

                # 解析listen配置
                parts = listen_config.split()
                port_info = {
                    'port': '80',  # 默认端口
                    'ip': '*',      # 默认监听所有IP
                    'server_name': server_names[0] if server_names else '默认主机',
                    'ssl_enabled': ssl_enabled,
                    'raw_config': listen_config
                }

                # 提取端口和IP
                addr_port = parts[0]
                if ':' in addr_port:
                    # 指定了IP地址
                    if addr_port.startswith('[') and ']:' in addr_port:
                        # IPv6地址
                        ip, port = addr_port.rsplit(':', 1)
                        port_info['ip'] = ip + ']'
                        port_info['port'] = port
                    else:
                        # IPv4地址
                        ip, port = addr_port.split(':', 1)
                        port_info['ip'] = ip
                        port_info['port'] = port
                else:
                    # 只有端口
                    port_info['port'] = addr_port

                # 检查其他参数
                if 'ssl' in parts:
                    port_info['ssl_enabled'] = True

                # 添加SSL证书信息
                if ssl_cert_match:
                    port_info['ssl_cert'] = ssl_cert_match.group(1).strip()
                if ssl_key_match:
                    port_info['ssl_key'] = ssl_key_match.group(1).strip()

                # 简化IP显示
                if port_info['ip'] == '*':
                    port_info['ip'] = '所有IP'
                elif port_info['ip'] == '0.0.0.0':
                    port_info['ip'] = '所有IPv4'
                elif port_info['ip'] == '[::]':
                    port_info['ip'] = '所有IPv6'

                listen_ports.append(port_info)

        return {
            'listen_ports': listen_ports,
            'total_count': len(listen_ports)
        }

    except Exception as e:
        logger.error(f'获取Nginx监听端口配置失败: {e}')
        return {
            'listen_ports': [],
            'total_count': 0
        }

def fetch_nginx_site_configs(config_file):
    """
    获取Nginx站点配置信息

    参数:
        config_file: Nginx主配置文件路径

    返回:
        list: 虚拟主机配置列表
    """
    try:
        site_configs = []

        # 读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()

        # 包含其他配置文件
        include_files = re.findall(r'include\s+([^;]+);', body)  # NOSONAR
        all_content = body

        for include_pattern in include_files:
            # 处理通配符
            if '*' in include_pattern:
                include_pattern = include_pattern.strip()
                if not include_pattern.startswith('/'):
                    # 相对路径，基于配置文件目录
                    config_dir = os.path.dirname(config_file)
                    include_pattern = os.path.join(config_dir, include_pattern)

                for include_file in glob.glob(include_pattern):
                    if os.path.exists(include_file):
                        try:
                            with open(include_file, 'r', encoding='utf-8') as f:
                                all_content += '\n' + f.read()
                        except Exception as e:
                            logger.warning(f'读取包含文件失败 {include_file}: {e}')

        # 查找server块
        server_blocks = re.findall(r'server\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', all_content, re.DOTALL)  # NOSONAR

        for server_block in server_blocks:
            site_config = {
                'server_name': '默认主机',
                'listen_ports': [],
                'root': '未配置',
                'index': '未配置',
                'ssl_enabled': False,
                'ssl_cert': None,
                'ssl_key': None,
                'locations': []
            }

            # 获取server_name
            server_name_matches = re.findall(r'server_name\s+([^;]+);', server_block)  # NOSONAR
            if server_name_matches:
                server_names = []
                for name_match in server_name_matches:
                    server_names.extend(name_match.strip().split())
                site_config['server_name'] = ', '.join(server_names)

            # 获取listen端口
            listen_matches = re.findall(r'listen\s+([^;]+);', server_block)  # NOSONAR
            for listen_match in listen_matches:
                addr_port = listen_match.strip().split()[0]
                port = addr_port.split(':')[-1] if ':' in addr_port else addr_port
                site_config['listen_ports'].append(port)

            # 获取root目录
            root_match = re.search(r'root\s+([^;]+);', server_block)  # NOSONAR
            if root_match:
                site_config['root'] = root_match.group(1).strip()

            # 获取index文件
            index_match = re.search(r'index\s+([^;]+);', server_block)  # NOSONAR
            if index_match:
                site_config['index'] = index_match.group(1).strip()

            # 检查SSL
            site_config['ssl_enabled'] = 'ssl' in server_block.lower()

            # 获取SSL证书
            ssl_cert_match = re.search(r'ssl_certificate\s+([^;]+);', server_block)  # NOSONAR
            if ssl_cert_match:
                site_config['ssl_cert'] = ssl_cert_match.group(1).strip()

            ssl_key_match = re.search(r'ssl_certificate_key\s+([^;]+);', server_block)  # NOSONAR
            if ssl_key_match:
                site_config['ssl_key'] = ssl_key_match.group(1).strip()

            # 获取location配置
            location_blocks = re.findall(r'location\s+([^{]*)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', server_block, re.DOTALL)  # NOSONAR
            for location_match in location_blocks:
                location_path = location_match[0].strip()
                location_config = location_match[1]

                location_info = {
                    'path': location_path,
                    'proxy_pass': None,
                    'root': None,
                    'index': None
                }

                # 获取proxy_pass
                proxy_pass_match = re.search(r'proxy_pass\s+([^;]+);', location_config)  # NOSONAR
                if proxy_pass_match:
                    location_info['proxy_pass'] = proxy_pass_match.group(1).strip()

                # 获取root
                root_match = re.search(r'root\s+([^;]+);', location_config)  # NOSONAR
                if root_match:
                    location_info['root'] = root_match.group(1).strip()

                # 获取index
                index_match = re.search(r'index\s+([^;]+);', location_config)  # NOSONAR
                if index_match:
                    location_info['index'] = index_match.group(1).strip()

                site_config['locations'].append(location_info)

            site_configs.append(site_config)

        return site_configs

    except Exception as e:
        logger.error(f'获取Nginx站点配置失败: {e}')
        return []

def fetch_system_port_status():
    """
    获取系统端口监听状态

    返回:
        list: 系统端口监听信息列表
    """
    try:
        ports = []

        # 使用ss命令获取监听端口
        output = subprocess.run(['ss', '-tulnp'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')[1:]  # 跳过标题行

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 7:
                    protocol = parts[0]
                    state = parts[1]
                    local_addr = parts[4]
                    proc_info = parts[6] if len(parts) > 6 else '-'

                    if state == 'LISTEN':
                        port_info = {
                            'protocol': protocol,
                            'local_addr': local_addr,
                            'state': state,
                            'process': proc_info
                        }

                        # 解析进程信息
                        if proc_info != '-':
                            # 格式通常是 "users:((\"nginx\",pid=1234,fd=8))"
                            pid_match = re.search(r'pid=(\d+)', proc_info)  # NOSONAR
                            if pid_match:
                                port_info['pid'] = pid_match.group(1)

                            # 提取进程名
                            proc_match = re.search(r'\"([^\"]+)\"', proc_info)  # NOSONAR
                            if proc_match:
                                port_info['process_name'] = proc_match.group(1)

                        ports.append(port_info)

        return ports

    except Exception as e:
        logger.error(f'获取系统端口监听状态失败: {e}')
        return []

def verify_port_conflicts(nginx_ports, system_ports):
    """
    检查端口冲突

    参数:
        nginx_ports: Nginx配置的监听端口列表
        system_ports: 系统实际监听端口列表

    返回:
        list: 端口冲突信息列表
    """
    try:
        conflicts = []

        # 创建系统端口映射
        system_port_map = {}
        for sys_port in system_ports:
            if 'local_addr' in sys_port:
                local_addr = sys_port['local_addr']
                if ':' in local_addr:
                    port = local_addr.split(':')[-1]
                    if port not in system_port_map:
                        system_port_map[port] = []
                    system_port_map[port].append(sys_port)

        # 检查Nginx配置端口
        for nginx_port in nginx_ports:
            port = nginx_port['port']
            if port in system_port_map:
                # 检查是否有其他进程占用
                for sys_port in system_port_map[port]:
                    process_name = sys_port.get('process_name', '未知进程')
                    if 'nginx' not in process_name.lower():
                        conflicts.append({
                            'port': port,
                            'nginx_process': nginx_port.get('server_name', 'Nginx'),
                            'other_process': process_name
                        })

        return conflicts

    except Exception as e:
        logger.error(f'检查端口冲突失败: {e}')
        return []

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_base_port",
    "function": fetch_nginx_base_port,
    "description": "获取Nginx监听的所有TCP/UDP端口、绑定IP以及端口对应的站点配置的MCP工具",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
