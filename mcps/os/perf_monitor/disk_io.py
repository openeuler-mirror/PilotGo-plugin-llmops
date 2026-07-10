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
def fetch_process_io(pid, interval):
    """
    获取指定进程的磁盘IO
    """
    io_info = {}

    try:
        # 第一次读取
        first_io = load_process_io(pid)

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取
        second_io = load_process_io(pid)

        if first_io and second_io:
            # 计算差值
            read_bytes = second_io['read_bytes'] - first_io['read_bytes']
            write_bytes = second_io['write_bytes'] - first_io['write_bytes']
            cancelled_write_bytes = second_io['cancelled_write_bytes'] - first_io['cancelled_write_bytes']

            # 计算速率
            read_speed = read_bytes / interval
            write_speed = write_bytes / interval

            # 格式化输出
            io_info['读速率'] = render_bytes_speed(read_speed)
            io_info['写速率'] = render_bytes_speed(write_speed)
            io_info['总速率'] = render_bytes_speed(read_speed + write_speed)
            io_info['取消的写字节数'] = f"{cancelled_write_bytes} 字节"

            # 获取进程名称
            comm = fetch_process_comm(pid)
            if comm:
                io_info['进程名称'] = comm

    except Exception as e:
        logger.error(f'获取指定进程的磁盘IO失败: {e}')

    return io_info
def fetch_all_process_io(interval):
    """
    获取所有进程的磁盘IO
    """
    process_list = []

    try:
        # 第一次读取所有进程的IO
        first_io_map = {}
        for pid in fetch_all_pids():
            io = load_process_io(pid)
            if io:
                first_io_map[pid] = io

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取所有进程的IO
        second_io_map = {}
        for pid in fetch_all_pids():
            io = load_process_io(pid)
            if io:
                second_io_map[pid] = io

        # 计算每个进程的IO速率
        for pid in first_io_map:
            if pid in second_io_map:
                first_io = first_io_map[pid]
                second_io = second_io_map[pid]

                # 计算差值
                read_bytes = second_io['read_bytes'] - first_io['read_bytes']
                write_bytes = second_io['write_bytes'] - first_io['write_bytes']

                # 计算速率
                read_speed = read_bytes / interval
                write_speed = write_bytes / interval
                total_speed = read_speed + write_speed

                # 只添加有IO活动的进程
                if total_speed > 0:
                    proc_info = {
                        'pid': pid,
                        'comm': fetch_process_comm(pid) or 'unknown',
                        'read_speed': render_bytes_speed(read_speed),
                        'write_speed': render_bytes_speed(write_speed),
                        'total_speed': render_bytes_speed(total_speed)
                    }
                    process_list.append(proc_info)

        # 按总速率排序
        process_list.sort(key=lambda x: analyze_speed(x['total_speed']), reverse=True)

        # 限制返回数量
        process_list = process_list[:10]  # 只返回前10个

    except Exception as e:
        logger.error(f'获取所有进程的磁盘IO失败: {e}')

    return process_list
def load_process_io(pid):
    """
    读取进程的IO信息
    """
    io_info = {}

    try:
        # 读取/proc/{pid}/io
        with open(f'/proc/{pid}/io', 'r') as f:
            lines = f.readlines()

            for line in lines:
                parts = line.strip().split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()

                    try:
                        val = int(value_str)
                        io_info[key] = val
                    except ValueError:
                        pass

    except Exception as e:
        # 忽略权限错误等异常
        pass

    return io_info
def fetch_all_pids():
    """
    获取所有进程ID
    """
    pids = []

    try:
        # 遍历/proc目录
        for item in os.listdir('/proc'):
            if item.isdigit():
                pids.append(item)

    except Exception as e:
        logger.error(f'获取所有进程ID失败: {e}')

    return pids
