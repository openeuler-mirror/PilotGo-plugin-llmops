#!/usr/bin/env python3

from datetime import datetime
import logging
import os
import re
import subprocess

import psutil
import pwd, grp

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_base_pid')


def fetch_nginx_base_pid():
    """
    获取Nginx进程PID信息的MCP工具，包括：
    - 主进程/工作进程PID列表
    - 进程归属用户/组
    - 进程启动时间
    - 进程运行状态
    - 进程资源使用情况
    - 进程树关系
    """
    try:
        output = []
        output.append('=== Nginx进程详细信息 ===')

        # 获取基本进程信息
        proc_info = get_nginx_process_info()
        if proc_info['state'] == '已停止':
            output.append('Nginx服务未运行')
            return '\n'.join(output)

        # 获取详细进程列表
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'username', 'create_time',
                                       'cpu_percent', 'memory_percent', 'state', 'ppid']):
            try:
                if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                        'username': proc.info['username'],
                        'create_time': proc.info['create_time'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent'],
                        'state': proc.info['state'],
                        'ppid': proc.info['ppid']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 分类主进程和工作进程
        master_procs = [p for p in processes if 'master' in p.get('cmdline', '').lower()]
        worker_procs = [p for p in processes if 'worker' in p.get('cmdline', '').lower()]

        # 显示主进程信息
        if master_procs:
            output.append('\n=== 主进程信息 ===')
            for proc in master_procs:
                output.extend(render_process_info(proc, '主进程'))

        # 显示工作进程信息
        if worker_procs:
            output.append(f'\n=== 工作进程信息 (共 {len(worker_procs)} 个) ===')
            for i, proc in enumerate(worker_procs, 1):
                output.extend(render_process_info(proc, f'工作进程 #{i}'))

        # 进程统计信息
        output.append('\n=== 进程统计 ===')
        output.append(f'总进程数: {len(processes)}')
        output.append(f'主进程数: {len(master_procs)}')
        output.append(f'工作进程数: {len(worker_procs)}')

        # 进程树关系
        process_tree = fetch_process_tree(processes)
        if process_tree:
            output.append('\n=== 进程树关系 ===')
            output.append(process_tree)

        # 资源使用统计
        resource_stats = fetch_resource_statistics(processes)
        if resource_stats:
            output.append('\n=== 资源使用统计 ===')
            output.append(resource_stats)

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx进程信息失败: {e}')
        return f'获取Nginx进程信息失败: {e}'
