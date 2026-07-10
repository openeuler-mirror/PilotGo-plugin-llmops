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
def fetch_cpu_usage(interval):
    """
    获取CPU使用率
    """
    try:
        # 读取/proc/stat文件
        def load_cpu_stats():
            stats = {}
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('cpu'):
                        parts = line.strip().split()
                        if parts[0] == 'cpu':
                            # 总体CPU
                            stats['total'] = {
                                'user': int(parts[1]),
                                'nice': int(parts[2]),
                                'system': int(parts[3]),
                                'idle': int(parts[4]),
                                'iowait': int(parts[5]),
                                'irq': int(parts[6]),
                                'softirq': int(parts[7])
                            }
                        elif parts[0].startswith('cpu') and parts[0][3:].isdigit():
                            # 每个核心
                            core = parts[0][3:]
                            stats[core] = {
                                'user': int(parts[1]),
                                'nice': int(parts[2]),
                                'system': int(parts[3]),
                                'idle': int(parts[4]),
                                'iowait': int(parts[5]),
                                'irq': int(parts[6]),
                                'softirq': int(parts[7])
                            }
            return stats

        # 第一次读取
        stats1 = load_cpu_stats()

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取
        stats2 = load_cpu_stats()

        # 计算使用率
        usage = {}
        for key in stats1:
            if key in stats2:
                stat1 = stats1[key]
                stat2 = stats2[key]

                # 计算总时间差
                total_diff = sum(stat2.values()) - sum(stat1.values())

                if total_diff > 0:
                    usage[key] = {
                        'user': round((stat2['user'] - stat1['user']) / total_diff * 100, 2),
                        'nice': round((stat2['nice'] - stat1['nice']) / total_diff * 100, 2),
                        'system': round((stat2['system'] - stat1['system']) / total_diff * 100, 2),
                        'idle': round((stat2['idle'] - stat1['idle']) / total_diff * 100, 2),
                        'iowait': round((stat2['iowait'] - stat1['iowait']) / total_diff * 100, 2),
                        'irq': round((stat2['irq'] - stat1['irq']) / total_diff * 100, 2),
                        'softirq': round((stat2['softirq'] - stat1['softirq']) / total_diff * 100, 2)
                    }

        return usage

    except Exception as e:
        logger.error(f'获取CPU使用率失败: {e}')
        return {}
