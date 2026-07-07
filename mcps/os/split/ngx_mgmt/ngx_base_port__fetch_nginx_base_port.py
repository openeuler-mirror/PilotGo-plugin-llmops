#!/usr/bin/env python3

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
