from datetime import datetime, timedelta
import logging
import os
import re
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_disk_history')

def fetch_perf_disk_history(duration=None, interval=None, device=None):
    """
    采集磁盘历史性能（按时间粒度的IOPS/读写速率/峰值/平均响应时间）

    参数:
        duration: 采集持续时间（秒），如 "60"
        interval: 采样间隔（秒），如 "5"
        device: 设备名称，如 "sda"

    返回:
        格式化的磁盘历史性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 磁盘历史性能 ===')

        # 确定采集参数
        if duration:
            try:
               采集_duration = int(duration)
            except ValueError:
                output.append(f'错误: 无效的采集持续时间 {duration}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            采集_duration = 60  # 默认60秒

        if interval:
            try:
                采样_interval = int(interval)
            except ValueError:
                output.append(f'错误: 无效的采样间隔 {interval}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            采样_interval = 5  # 默认5秒

        # 检查参数有效性
        if 采样_interval <= 0:
            output.append('错误: 采样间隔必须大于0')
            output.append('=====================')
            return '\n'.join(output)

        if 采集_duration <= 0:
            output.append('错误: 采集持续时间必须大于0')
            output.append('=====================')
            return '\n'.join(output)

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

        output.append(f'采集持续时间: {采集_duration}秒')
        output.append(f'采样间隔: {采样_interval}秒')
        output.append(f"监控设备: {', '.join(devices)}")

        # 计算采样次数
        sample_count = 采集_duration // 采样_interval
        if sample_count < 1:
            sample_count = 1

        # 开始采集
        output.append(f'\n开始采集，共 {sample_count} 个样本...')

        # 存储采集数据
        device_samples = {dev: [] for dev in devices}
        timestamps = []

        # 开始时间
        start_time = datetime.now()

        for i in range(sample_count):
            # 记录时间戳
            current_time = datetime.now()
            timestamps.append(current_time.strftime('%H:%M:%S'))

            # 采集磁盘性能数据
            disk_stats = fetch_disk_stats(devices, 1.0)  # 每次采样间隔1秒
            if disk_stats:
                for dev, stats in disk_stats.items():
                    device_samples[dev].append(stats)

            # 等待下一次采样
            if i < sample_count - 1:
                time.sleep(采样_interval - 1)  # 减去1秒的采样时间

        # 结束时间
        end_time = datetime.now()

        # 计算实际采集时间
        actual_duration = (end_time - start_time).total_seconds()
        output.append(f'\n实际采集时间: {actual_duration:.2f}秒')

        # 分析每个设备的数据
        for dev, samples in device_samples.items():
            if samples:
                output.append(f"\n设备 {dev} 统计:")

                # 提取各项指标
                metrics = {
                    '读IOPS': [],
                    '写IOPS': [],
                    '总IOPS': [],
                    '读速率': [],
                    '写速率': [],
                    '总速率': [],
                    '平均读响应时间': [],
                    '平均写响应时间': [],
                    '忙占比': []
                }

                # 解析样本数据
                for sample in samples:
                    for key, value in sample.items():
                        if key in metrics:
                            # 提取数值
                            if '速率' in key:
                                # 提取MB/s数值
                                match = re.search(r'(\d+\.\d+)', value)  # NOSONAR
                                if match:
                                    metrics[key].append(float(match.group(1)))
                            elif 'IOPS' in key:
                                # 提取IOPS数值
                                match = re.search(r'(\d+\.\d+)', value)  # NOSONAR
                                if match:
                                    metrics[key].append(float(match.group(1)))
                            elif '响应时间' in key:
                                # 提取毫秒数值
                                match = re.search(r'(\d+\.\d+)', value)  # NOSONAR
                                if match:
                                    metrics[key].append(float(match.group(1)))
                            elif '忙占比' in key:
                                # 提取百分比数值
                                match = re.search(r'(\d+\.\d+)', value)  # NOSONAR
                                if match:
                                    metrics[key].append(float(match.group(1)))

                # 计算统计值
                for metric, values in metrics.items():
                    if values:
                        max_value = max(values)
                        min_value = min(values)
                        avg_value = sum(values) / len(values)

                        # 格式化输出
                        if '速率' in metric:
                            output.append(f"  {metric}:")
                            output.append(f"    最大值: {max_value:.2f} MB/s")
                            output.append(f"    最小值: {min_value:.2f} MB/s")
                            output.append(f"    平均值: {avg_value:.2f} MB/s")
                        elif 'IOPS' in metric:
                            output.append(f"  {metric}:")
                            output.append(f"    最大值: {max_value:.2f}")
                            output.append(f"    最小值: {min_value:.2f}")
                            output.append(f"    平均值: {avg_value:.2f}")
                        elif '响应时间' in metric:
                            output.append(f"  {metric}:")
                            output.append(f"    最大值: {max_value:.2f} ms")
                            output.append(f"    最小值: {min_value:.2f} ms")
                            output.append(f"    平均值: {avg_value:.2f} ms")
                        elif '忙占比' in metric:
                            output.append(f"  {metric}:")
                            output.append(f"    最大值: {max_value:.2f}%")
                            output.append(f"    最小值: {min_value:.2f}%")
                            output.append(f"    平均值: {avg_value:.2f}%")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取磁盘历史性能失败: {e}')
        return f'获取磁盘历史性能失败: {e}'
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
