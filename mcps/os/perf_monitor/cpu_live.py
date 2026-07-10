import logging
import os
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_cpu_real')

def fetch_perf_cpu_real(interval=None):
    """
    采集CPU实时性能（每个CPU核心的使用率/空闲/系统/用户/软中断/硬中断占比）

    参数:
        interval: 采样间隔（秒），如 "1"

    返回:
        格式化的CPU实时性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== CPU实时性能 ===')

        # 确定采样间隔
        if interval:
            try:
                sample_interval = float(interval)
            except ValueError:
                output.append(f'错误: 无效的采样间隔 {interval}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            sample_interval = 1.0

        # 获取CPU核心数
        cpu_count = fetch_cpu_count()
        output.append(f'CPU核心数: {cpu_count}')

        # 获取CPU使用率
        cpu_usage = fetch_cpu_usage(sample_interval)
        if cpu_usage:
            # 显示总体CPU使用率
            if 'total' in cpu_usage:
                output.append('\n总体CPU使用率:')
                total_usage = cpu_usage['total']
                for key, value in total_usage.items():
                    output.append(f"  {key}: {value}%")

            # 显示每个核心的使用率
            output.append('\n各核心CPU使用率:')
            for core in range(cpu_count):
                if str(core) in cpu_usage:
                    core_usage = cpu_usage[str(core)]
                    output.append(f"\n核心 {core}:")
                    for key, value in core_usage.items():
                        output.append(f"  {key}: {value}%")
        else:
            output.append('无法获取CPU使用率')

        # 显示系统负载
        load_avg = fetch_load_average()
        if load_avg:
            output.append('\n系统负载:')
            for key, value in load_avg.items():
                output.append(f"  {key}: {value}")

        # 显示采样信息
        output.append('\n采样信息:')
        output.append(f"采样间隔: {sample_interval}秒")
        output.append(f"采样时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取CPU实时性能失败: {e}')
        return f'获取CPU实时性能失败: {e}'
def fetch_cpu_count():
    """
    获取CPU核心数
    """
    try:
        # 从/proc/cpuinfo获取
        with open('/proc/cpuinfo', 'r') as f:
            body = f.read()
            return body.count('processor\t:')
    except Exception:
        return 0
