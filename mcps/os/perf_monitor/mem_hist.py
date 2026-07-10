from datetime import datetime, timedelta
import logging
import os
import re
import subprocess
import time

import psutil

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_mem_history')

def fetch_perf_mem_history(duration=None, interval=None):
    """
    采集内存历史性能（内存使用率/交换分区使用/换入换出/按时间粒度统计）

    参数:
        duration: 采集持续时间（秒），如 "60"
        interval: 采样间隔（秒），如 "5"

    返回:
        格式化的内存历史性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 内存历史性能 ===')

        # 确定采集参数
        if duration is not None:
            try:
               collection_duration = int(duration)
            except ValueError:
                output.append(f'错误: 无效的采集持续时间 {duration}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            collection_duration = 60  # 默认60秒

        if interval:
            try:
                sample_interval = int(interval)
            except ValueError:
                output.append(f'错误: 无效的采样间隔 {interval}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            sample_interval = 5  # 默认5秒

        # 检查参数有效性
        if sample_interval <= 0:
            output.append('错误: 采样间隔必须大于0')
            output.append('=====================')
            return '\n'.join(output)

        if collection_duration <= 0:
            output.append('错误: 采集持续时间必须大于0')
            output.append('=====================')
            return '\n'.join(output)

        output.append(f'采集持续时间: {collection_duration}秒')
        output.append(f'采样间隔: {sample_interval}秒')

        # 计算采样次数
        sample_count = collection_duration // sample_interval
        if sample_count < 1:
            sample_count = 1

        # 开始采集
        output.append(f'\n开始采集，共 {sample_count} 个样本...')

        # 存储采集数据
        mem_samples = []
        swap_samples = []
        timestamps = []

        # 开始时间
        start_time = datetime.now()

        for i in range(sample_count):
            # 记录时间戳
            current_time = datetime.now()
            timestamps.append(current_time.strftime('%H:%M:%S'))

            # 采集内存信息
            mem_data = fetch_memory_snapshot()
            if mem_data:
                mem_samples.append(mem_data)

            # 采集交换分区信息
            swap_info = fetch_swap_snapshot()
            if swap_info:
                swap_samples.append(swap_info)

            # 等待下一次采样
            if i < sample_count - 1:
                time.sleep(sample_interval)

        # 结束时间
        end_time = datetime.now()

        # 计算实际采集时间
        actual_duration = (end_time - start_time).total_seconds()
        output.append(f'\n实际采集时间: {actual_duration:.2f}秒')

        # 分析内存数据
        if mem_samples:
            # 提取内存使用率
            mem_usage_values = []
            for sample in mem_samples:
                if '内存使用率' in sample:
                    try:
                        mem_usage_values.append(float(sample['内存使用率'].rstrip('%')))
                    except ValueError:
                        pass

            if mem_usage_values:
                # 计算统计值
                max_mem_usage = max(mem_usage_values)
                min_mem_usage = min(mem_usage_values)
                avg_mem_usage = sum(mem_usage_values) / len(mem_usage_values)

                output.append('\n内存使用率统计:')
                output.append(f"  最大值: {max_mem_usage:.2f}%")
                output.append(f"  最小值: {min_mem_usage:.2f}%")
                output.append(f"  平均值: {avg_mem_usage:.2f}%")

            # 提取可用内存
            available_mem_values = []
            for sample in mem_samples:
                if '可用内存' in sample:
                    # 提取数值部分
                    mem_str = sample['可用内存']
                    match = re.search(r'(\d+)\s*(\w+)', mem_str)  # NOSONAR
                    if match:
                        val = int(match.group(1))
                        unit = match.group(2)
                        # 转换为KB
                        if unit == 'GB':
                            val *= 1024 * 1024
                        elif unit == 'MB':
                            val *= 1024
                        available_mem_values.append(val)

            if available_mem_values:
                # 计算统计值
                max_available = max(available_mem_values)
                min_available = min(available_mem_values)
                avg_available = sum(available_mem_values) / len(available_mem_values)

                output.append('\n可用内存统计:')
                output.append(f"  最大值: {render_memory(max_available)}")
                output.append(f"  最小值: {render_memory(min_available)}")
                output.append(f"  平均值: {render_memory(int(avg_available))}")

        # 分析交换分区数据
        if swap_samples:
            # 提取交换分区使用率
            swap_usage_values = []
            for sample in swap_samples:
                if '交换分区使用率' in sample:
                    try:
                        swap_usage_values.append(float(sample['交换分区使用率'].rstrip('%')))
                    except ValueError:
                        pass

            if swap_usage_values:
                # 计算统计值
                max_swap_usage = max(swap_usage_values)
                min_swap_usage = min(swap_usage_values)
                avg_swap_usage = sum(swap_usage_values) / len(swap_usage_values)

                output.append('\n交换分区使用率统计:')
                output.append(f"  最大值: {max_swap_usage:.2f}%")
                output.append(f"  最小值: {min_swap_usage:.2f}%")
                output.append(f"  平均值: {avg_swap_usage:.2f}%")

        # 显示内存换入换出信息
        page_stats = fetch_page_stats()
        if page_stats:
            output.append('\n内存换入换出统计:')
            for key, val in page_stats.items():
                output.append(f"  {key}: {val}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取内存历史性能失败: {e}')
        return f'获取内存历史性能失败: {e}'
