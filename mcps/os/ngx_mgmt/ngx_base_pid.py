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

def render_process_info(proc_info, process_type):
    """格式化进程信息"""
    output = []
    try:
        output.append(f'{process_type}:')
        output.append(f'  PID: {proc_info["pid"]}')
        output.append(f'  进程名: {proc_info["name"]}')
        output.append(f'  用户名: {proc_info["username"]}')

        # 用户组信息
        try:
            user_info = pwd.getpwnam(proc_info["username"])
            group_info = grp.getgrgid(user_info.pw_gid)
            output.append(f'  用户组: {group_info.gr_name} (GID: {user_info.pw_gid})')
        except Exception:
            output.append(f'  用户组: 获取失败')

        # 启动时间
        if proc_info["create_time"]:
            start_time = datetime.fromtimestamp(proc_info["create_time"])
            uptime = datetime.now() - start_time
            output.append(f'  启动时间: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
            output.append(f'  运行时长: {uptime.days}天 {uptime.seconds//3600}小时 {(uptime.seconds%3600)//60}分钟')

        # 进程状态
        status_map = {'running': '运行中', 'sleeping': '睡眠中', 'stopped': '已停止'}
        state = status_map.get(proc_info["state"], proc_info["state"])
        output.append(f'  进程状态: {state}')

        # 资源使用
        if proc_info["cpu_percent"] is not None:
            output.append(f'  CPU使用率: {proc_info["cpu_percent"]:.1f}%')
        if proc_info["memory_percent"] is not None:
            output.append(f'  内存使用率: {proc_info["memory_percent"]:.1f}%')

        # 命令行参数
        if proc_info["cmdline"]:
            output.append(f'  命令行: {proc_info["cmdline"]}')

        output.append('')  # 空行分隔
    except Exception as e:
        logger.error(f'格式化进程信息失败: {e}')
    return output

def fetch_process_tree(processes):
    """获取进程树关系"""
    try:
        output = []
        process_dict = {p['pid']: p for p in processes}

        def build_tree(pid, level=0):
            proc = process_dict.get(pid)
            if not proc: return
            indent = '  ' * level
            output.append(f'{indent}└─ {proc["name"]} (PID: {pid})')
            children = [p for p in processes if p['ppid'] == pid]
            for child in children:
                build_tree(child['pid'], level + 1)

        # 从根进程开始构建
        root_pids = [p['pid'] for p in processes if p['ppid'] not in process_dict or p['ppid'] == 0]
        if root_pids:
            output.append('进程树结构:')
            for pid in root_pids:
                build_tree(pid)
            return '\n'.join(output)
        return ''
    except Exception as e:
        logger.error(f'构建进程树失败: {e}')
        return ''

def fetch_resource_statistics(processes):
    """获取资源使用统计"""
    try:
        total_cpu = sum(p['cpu_percent'] for p in processes if p['cpu_percent'] is not None)
        total_mem = sum(p['memory_percent'] for p in processes if p['memory_percent'] is not None)
        count = len(processes)

        output = [
            f'CPU总使用率: {total_cpu:.1f}%',
            f'内存总使用率: {total_mem:.1f}%',
            f'平均CPU使用率: {total_cpu/count:.1f}%' if count else '0%',
            f'平均内存使用率: {total_mem/count:.1f}%' if count else '0%'
        ]
        return '\n'.join(output)
    except Exception as e:
        logger.error(f'获取资源统计失败: {e}')
        return ''

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_nginx_base_pid",
    "function": fetch_nginx_base_pid,
    "description": "获取Nginx进程详细信息，包括PID、用户/组、资源使用和进程树关系",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
