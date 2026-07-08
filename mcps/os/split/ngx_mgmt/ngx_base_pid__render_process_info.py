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
