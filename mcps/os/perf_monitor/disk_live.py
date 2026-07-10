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
