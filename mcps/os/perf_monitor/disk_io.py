import logging
import os
import re
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_disk_io')

def fetch_perf_disk_io(pid=None, interval=None):
    """
    采集进程磁盘IO（指定进程/所有进程的磁盘读写速率/IO占用排序）

    参数:
        pid: 进程ID，如 "1234"
        interval: 采样间隔（秒），如 "1"

    返回:
        格式化的进程磁盘IO信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 进程磁盘IO ===')

        # 确定采样间隔
        if interval:
            try:
                sample_interval = float(interval)
            except ValueError:
                output.append(f'错误: 无效的采样间隔 {interval}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            sample_interval = 1.0  # 默认1秒

        output.append(f'采样间隔: {sample_interval}秒')

        if pid:
            # 检查进程是否存在
            if not os.path.exists(f'/proc/{pid}'):
                output.append(f'错误: 进程 {pid} 不存在')
                output.append('=====================')
                return '\n'.join(output)

            # 采集指定进程的磁盘IO
            process_io = fetch_process_io(pid, sample_interval)
            if process_io:
                output.append(f"\n进程 {pid} 磁盘IO:")
                for key, val in process_io.items():
                    output.append(f"  {key}: {val}")
            else:
                output.append(f'无法获取进程 {pid} 的磁盘IO信息')
        else:
            # 采集所有进程的磁盘IO
            all_process_io = fetch_all_process_io(sample_interval)
            if all_process_io:
                output.append('\n所有进程磁盘IO（按IO占用排序）:')
                for proc_info in all_process_io:
                    output.append(f"  PID {proc_info['pid']} - {proc_info['comm']}:")
                    output.append(f"    读速率: {proc_info['read_speed']}")
                    output.append(f"    写速率: {proc_info['write_speed']}")
                    output.append(f"    总速率: {proc_info['total_speed']}")
            else:
                output.append('无法获取所有进程的磁盘IO信息')

        # 获取系统磁盘IO统计
        system_io = fetch_system_io_stats()
        if system_io:
            output.append('\n系统磁盘IO统计:')
            for key, val in system_io.items():
                output.append(f"  {key}: {val}")

        # 获取磁盘设备IO
        disk_io = fetch_disk_io_stats()
        if disk_io:
            output.append('\n磁盘设备IO:')
            for dev, io_stats in disk_io.items():
                output.append(f"  {dev}:")
                output.append(f"    读速率: {io_stats['read_speed']}")
                output.append(f"    写速率: {io_stats['write_speed']}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取进程磁盘IO失败: {e}')
        return f'获取进程磁盘IO失败: {e}'
