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
logger = logging.getLogger('perf_cpu_history')

def fetch_perf_cpu_history(duration=None, interval=None):
    """
    采集CPU历史性能（按时间粒度的CPU使用率/负载变化/峰值/平均值）

    参数:
        duration: 采集持续时间（秒），如 "60"
        interval: 采样间隔（秒），如 "5"

    返回:
        格式化的CPU历史性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== CPU历史性能 ===')

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

        output.append(f'采集持续时间: {采集_duration}秒')
        output.append(f'采样间隔: {采样_interval}秒')

        # 计算采样次数
        sample_count = 采集_duration // 采样_interval
        if sample_count < 1:
            sample_count = 1

        # 开始采集
        output.append(f'\n开始采集，共 {sample_count} 个样本...')

        # 存储采集数据
        cpu_samples = []
        load_samples = []
        timestamps = []

        # 开始时间
        start_time = datetime.now()

        for i in range(sample_count):
            # 记录时间戳
            current_time = datetime.now()
            timestamps.append(current_time.strftime('%H:%M:%S'))

            # 采集CPU使用率
            cpu_usage = fetch_cpu_usage(1.0)  # 1秒采样
            if cpu_usage and 'total' in cpu_usage:
                cpu_samples.append(cpu_usage['total'])

            # 采集系统负载
            load_avg = fetch_load_average()
            if load_avg:
                load_samples.append(load_avg)

            # 等待下一次采样
            if i < sample_count - 1:
                time.sleep(采样_interval - 1)  # 减去1秒的采样时间

        # 结束时间
        end_time = datetime.now()

        # 计算实际采集时间
        actual_duration = (end_time - start_time).total_seconds()
        output.append(f'\n实际采集时间: {actual_duration:.2f}秒')

        # 分析数据
        if cpu_samples:
            # 显示CPU使用率趋势
            output.append('\nCPU使用率趋势:')

            # 提取各项指标的最大值、最小值和平均值
            metrics = ['user', 'system', 'idle', 'iowait', 'irq', 'softirq']
            metric_stats = {}

            for metric in metrics:
                values = [sample[metric] for sample in cpu_samples if metric in sample]
                if values:
                    metric_stats[metric] = {
                        'max': max(values),
                        'min': min(values),
                        'avg': sum(values) / len(values)
                    }

            # 显示统计结果
            output.append('\nCPU使用率统计:')
            for metric, stats in metric_stats.items():
                output.append(f"  {metric}:")
                output.append(f"    最大值: {stats['max']:.2f}%")
                output.append(f"    最小值: {stats['min']:.2f}%")
                output.append(f"    平均值: {stats['avg']:.2f}%")

        if load_samples:
            # 显示系统负载趋势
            output.append('\n系统负载趋势:')

            # 提取各项指标的最大值、最小值和平均值
            load_metrics = ['1分钟负载', '5分钟负载', '15分钟负载']
            load_stats = {}

            for metric in load_metrics:
                values = []
                for sample in load_samples:
                    if metric in sample:
                        try:
                            values.append(float(sample[metric]))
                        except ValueError:
                            pass
                if values:
                    load_stats[metric] = {
                        'max': max(values),
                        'min': min(values),
                        'avg': sum(values) / len(values)
                    }

            # 显示统计结果
            output.append('\n系统负载统计:')
            for metric, stats in load_stats.items():
                output.append(f"  {metric}:")
                output.append(f"    最大值: {stats['max']:.2f}")
                output.append(f"    最小值: {stats['min']:.2f}")
                output.append(f"    平均值: {stats['avg']:.2f}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取CPU历史性能失败: {e}')
        return f'获取CPU历史性能失败: {e}'
