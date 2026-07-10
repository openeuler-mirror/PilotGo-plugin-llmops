import logging
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(label)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('perf_irq')

def fetch_perf_irq(interval=None):
    """
    采集中断实时性能（中断次数/高频中断源/中断占用CPU/硬中断/软中断统计）

    参数:
        interval: 采样间隔（秒），如 "1"

    返回:
        格式化的中断实时性能信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 中断实时性能 ===')

        # 确定采样间隔
        if interval is not None:
            try:
                sample_interval = float(interval)
                if sample_interval <= 0:
                    output.append('错误: 采样间隔必须大于0')
                    output.append('=====================')
                    return '\n'.join(output)
            except ValueError:
                output.append(f'错误: 无效的采样间隔 {interval}')
                output.append('=====================')
                return '\n'.join(output)
        else:
            sample_interval = 1.0  # 默认1秒

        output.append(f'采样间隔: {sample_interval}秒')

        # 检查中断相关文件是否存在
        if not os.path.exists('/proc/interrupts'):
            output.append('错误: 无法获取系统中断信息')
            output.append('=====================')
            return '\n'.join(output)

        # 采集硬中断统计
        hardirq_stats = fetch_hardirq_stats(sample_interval)
        if hardirq_stats:
            output.append('\n硬中断统计:')
            for irq, count in hardirq_stats.items():
                output.append(f"  IRQ {irq}: {count} 次/秒")

        # 采集软中断统计
        softirq_stats = fetch_softirq_stats(sample_interval)
        if softirq_stats:
            output.append('\n软中断统计:')
            for irq, count in softirq_stats.items():
                output.append(f"  {irq}: {count} 次/秒")

        # 采集高频中断源
        high_freq_irqs = fetch_high_frequency_irqs()
        if high_freq_irqs:
            output.append('\n高频中断源:')
            for irq_info in high_freq_irqs:
                output.append(f"  IRQ {irq_info['irq']} - {irq_info['label']}: {irq_info['count']} 次")

        # 采集中断占用CPU
        irq_cpu_usage = fetch_irq_cpu_usage()
        if irq_cpu_usage:
            output.append('\n中断占用CPU:')
            for cpu, usage in irq_cpu_usage.items():
                output.append(f"  CPU {cpu}: {usage}")

        # 采集系统中断配置
        irq_config = fetch_irq_config()
        if irq_config:
            output.append('\n中断配置:')
            for key, val in irq_config.items():
                output.append(f"  {key}: {val}")

        # 采集中断亲和性
        irq_affinity = fetch_irq_affinity()
        if irq_affinity:
            output.append('\n中断亲和性:')
            for irq, affinity in irq_affinity.items():
                output.append(f"  IRQ {irq}: {affinity}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取中断实时性能失败: {e}')
        return f'获取中断实时性能失败: {e}'
def fetch_hardirq_stats(interval):
    """
    获取硬中断统计
    """
    stats = {}

    try:
        # 第一次读取
        first_irqs = load_irq_stats()

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取
        second_irqs = load_irq_stats()

        # 计算中断频率
        for irq, count in second_irqs.items():
            if irq in first_irqs:
                diff = count - first_irqs[irq]
                if diff > 0:
                    frequency = diff / interval
                    stats[irq] = frequency

    except Exception as e:
        logger.error(f'获取硬中断统计失败: {e}')

    return stats
def fetch_softirq_stats(interval):
    """
    获取软中断统计
    """
    stats = {}

    try:
        # 第一次读取
        first_softirqs = load_softirq_stats()

        # 等待指定间隔
        time.sleep(interval)

        # 第二次读取
        second_softirqs = load_softirq_stats()

        # 计算软中断频率
        for irq, count in second_softirqs.items():
            if irq in first_softirqs:
                diff = count - first_softirqs[irq]
                if diff > 0:
                    frequency = diff / interval
                    stats[irq] = frequency

    except Exception as e:
        logger.error(f'获取软中断统计失败: {e}')

    return stats
def load_irq_stats():
    """
    读取硬中断统计
    """
    stats = {}

    try:
        with open('/proc/interrupts', 'r') as f:
            lines = f.readlines()

            for line in lines[1:]:  # 跳过表头
                parts = line.strip().split()
                if len(parts) >= 2:
                    irq = parts[0].rstrip(':')
                    # 计算所有CPU的中断次数总和
                    total = 0
                    for part in parts[1:]:
                        if part.isdigit():
                            total += int(part)
                        else:
                            break
                    stats[irq] = total

    except Exception as e:
        logger.error(f'读取硬中断统计失败: {e}')

    return stats
def load_softirq_stats():
    """
    读取软中断统计
    """
    stats = {}

    try:
        with open('/proc/softirqs', 'r') as f:
            lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    irq = parts[0].rstrip(':')
                    # 计算所有CPU的软中断次数总和
                    total = 0
                    for part in parts[1:]:
                        if part.isdigit():
                            total += int(part)
                        else:
                            break
                    stats[irq] = total

    except Exception as e:
        logger.error(f'读取软中断统计失败: {e}')

    return stats
