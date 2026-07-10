import logging
import os
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_disk_real')

def fetch_perf_disk_real(interval=None, device=None):
    """
    采集磁盘实时性能（磁盘IOPS/读写速率/平均响应时间/队列长度/忙占比）

    参数:
        interval: 采样间隔（秒），如 "1"
        device: 设备名称，如 "sda"

    返回:
        格式化的磁盘实时性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 磁盘实时性能 ===')

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

        # 获取磁盘设备列表
        devices = []
        if device:
            # 检查设备是否存在
            if os.path.exists(f'/sys/block/{device}'):
                devices.append(device)
            else:
                output.append(f'错误: 设备 {device} 不存在')
                output.append('=====================')
                return '\n'.join(output)
        else:
            # 获取所有磁盘设备
            devices = fetch_disk_devices()

        if not devices:
            output.append('无法获取磁盘设备列表')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'采样间隔: {sample_interval}秒')
        output.append(f"监控设备: {', '.join(devices)}")

        # 采集磁盘性能数据
        disk_stats = fetch_disk_stats(devices, sample_interval)
        if disk_stats:
            # 显示每个设备的性能数据
            for dev, stats in disk_stats.items():
                output.append(f"\n设备 {dev}:")
                for key, val in stats.items():
                    output.append(f"  {key}: {val}")
        else:
            output.append('无法获取磁盘性能数据')

        # 获取磁盘使用率
        disk_usage = fetch_disk_usage()
        if disk_usage:
            output.append('\n磁盘使用率:')
            for dev, usage in disk_usage.items():
                output.append(f"  {dev}: {usage}")

        # 显示系统磁盘IO统计
        system_io = fetch_system_io_stats()
        if system_io:
            output.append('\n系统磁盘IO统计:')
            for key, val in system_io.items():
                output.append(f"  {key}: {val}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取磁盘实时性能失败: {e}')
        return f'获取磁盘实时性能失败: {e}'
def fetch_disk_devices():
    """
    获取磁盘设备列表
    """
    devices = []

    try:
        # 读取/sys/block目录
        block_dir = '/sys/block'
        if os.path.exists(block_dir):
            for item in os.listdir(block_dir):
                # 排除虚拟设备
                if not item.startswith('loop') and not item.startswith('ram') and not item.startswith('dm-'):
                    devices.append(item)

    except Exception as e:
        logger.error(f'获取磁盘设备列表失败: {e}')

    return devices
def fetch_disk_stats(devices, interval):
    """
    获取磁盘性能数据
    """
    stats = {}

    try:
        # 第一次读取
        first_stats = {}
        for dev in devices:
            first_stats[dev] = load_disk_stats(dev)

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取
        second_stats = {}
        for dev in devices:
            second_stats[dev] = load_disk_stats(dev)

        # 计算性能数据
        for dev in devices:
            if dev in first_stats and dev in second_stats:
                stat1 = first_stats[dev]
                stat2 = second_stats[dev]

                # 计算差值
                reads_completed = stat2['reads_completed'] - stat1['reads_completed']
                writes_completed = stat2['writes_completed'] - stat1['writes_completed']
                read_sectors = stat2['read_sectors'] - stat1['read_sectors']
                write_sectors = stat2['write_sectors'] - stat1['write_sectors']
                read_time = stat2['read_time'] - stat1['read_time']
                write_time = stat2['write_time'] - stat1['write_time']
                io_time = stat2['io_time'] - stat1['io_time']

                # 计算性能指标
                # 假设每个扇区512字节
                sector_size = 512

                # IOPS
                read_iops = reads_completed / interval
                write_iops = writes_completed / interval
                total_iops = read_iops + write_iops

                # 读写速率
                read_speed = (read_sectors * sector_size) / interval / 1024 / 1024  # MB/s
                write_speed = (write_sectors * sector_size) / interval / 1024 / 1024  # MB/s
                total_speed = read_speed + write_speed

                # 平均响应时间（毫秒）
                avg_read_time = (read_time / reads_completed) if reads_completed > 0 else 0
                avg_write_time = (write_time / writes_completed) if writes_completed > 0 else 0

                # 忙占比
                busy_percent = (io_time / (interval * 1000)) * 100  # 1000毫秒/秒
                if busy_percent > 100:
                    busy_percent = 100

                # 存储性能数据
                stats[dev] = {
                    '读IOPS': f"{read_iops:.2f}",
                    '写IOPS': f"{write_iops:.2f}",
                    '总IOPS': f"{total_iops:.2f}",
                    '读速率': f"{read_speed:.2f} MB/s",
                    '写速率': f"{write_speed:.2f} MB/s",
                    '总速率': f"{total_speed:.2f} MB/s",
                    '平均读响应时间': f"{avg_read_time:.2f} ms",
                    '平均写响应时间': f"{avg_write_time:.2f} ms",
                    '忙占比': f"{busy_percent:.2f}%"
                }

    except Exception as e:
        logger.error(f'获取磁盘性能数据失败: {e}')

    return stats
def load_disk_stats(device):
    """
    读取磁盘统计信息
    """
    stats = {
        'reads_completed': 0,
        'reads_merged': 0,
        'read_sectors': 0,
        'read_time': 0,
        'writes_completed': 0,
        'writes_merged': 0,
        'write_sectors': 0,
        'write_time': 0,
        'io_in_progress': 0,
        'io_time': 0,
        'weighted_io_time': 0
    }

    try:
        # 读取/proc/diskstats
        with open('/proc/diskstats', 'r') as f:
            lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 14:
                    dev_name = parts[2]
                    if dev_name == device:
                        stats['reads_completed'] = int(parts[3])
                        stats['reads_merged'] = int(parts[4])
                        stats['read_sectors'] = int(parts[5])
                        stats['read_time'] = int(parts[6])
                        stats['writes_completed'] = int(parts[7])
                        stats['writes_merged'] = int(parts[8])
                        stats['write_sectors'] = int(parts[9])
                        stats['write_time'] = int(parts[10])
                        stats['io_in_progress'] = int(parts[11])
                        stats['io_time'] = int(parts[12])
                        stats['weighted_io_time'] = int(parts[13])
                        break

    except Exception as e:
        logger.error(f'读取磁盘统计信息失败: {e}')

    return stats
def fetch_disk_usage():
    """
    获取磁盘使用率
    """
    usage = {}

    try:
        # 使用df命令获取磁盘使用率
        output = subprocess.run(['df', '-h'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines[1:]:  # 跳过表头
                parts = line.split()
                if len(parts) >= 6:
                    device = parts[0]
                    use_percent = parts[4]
                    usage[device] = use_percent

    except Exception as e:
        logger.error(f'获取磁盘使用率失败: {e}')

    return usage
def fetch_system_io_stats():
    """
    获取系统磁盘IO统计
    """
    stats = {}

    try:
        # 读取/proc/vmstat
        with open('/proc/vmstat', 'r') as f:
            lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) == 2:
                    key = parts[0]
                    val = parts[1]

                    # 提取IO相关统计
                    if key == 'pgpgin':
                        stats['换入页数'] = val
                    elif key == 'pgpgout':
                        stats['换出页数'] = val
                    elif key == 'pgfault':
                        stats['页错误数'] = val
                    elif key == 'pgmajfault':
                        stats['主页错误数'] = val

    except Exception as e:
        logger.error(f'获取系统磁盘IO统计失败: {e}')

    return stats

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_perf_disk_real",
    "function": fetch_perf_disk_real,
    "description": "采集磁盘实时性能（磁盘IOPS/读写速率/平均响应时间/队列长度/忙占比）",
    "parameters": {
        "type": "object",
        "properties": {
            "interval": {
                "type": "string",
                "description": "采样间隔（秒），如 \"1\""
            },
            "device": {
                "type": "string",
                "description": "设备名称，如 \"sda\""
            }
        },
        "required": []
    }
}
