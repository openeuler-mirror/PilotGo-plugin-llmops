import logging
import os
import subprocess
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_icmp')

def fetch_net_icmp():
    """
    采集ICMP协议状态（ICMP包收发数/丢包率/错包率/ICMP类型统计）

    返回:
        格式化的ICMP协议状态信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== ICMP协议状态 ===')

        # 采集ICMP包收发数
        icmp_stats = fetch_icmp_stats()
        if icmp_stats:
            output.append('\nICMP包收发数:')
            for key, value in icmp_stats.items():
                output.append(f"  {key}: {value}")

        # 计算丢包率和错包率
        icmp_rates = fetch_icmp_rates(icmp_stats)
        if icmp_rates:
            output.append('\nICMP包率统计:')
            for key, value in icmp_rates.items():
                output.append(f"  {key}: {value}")

        # 采集ICMP类型统计
        icmp_type_stats = fetch_icmp_type_stats()
        if icmp_type_stats:
            output.append('\nICMP类型统计:')
            for key, value in icmp_type_stats.items():
                output.append(f"  {key}: {value}")

        # 采集ICMP配置
        icmp_config = fetch_icmp_config()
        if icmp_config:
            output.append('\nICMP配置:')
            for key, value in icmp_config.items():
                output.append(f"  {key}: {value}")

        # 检查ICMP协议状态
        icmp_status = verify_icmp_status(icmp_stats)
        if icmp_status:
            output.append('\nICMP协议状态检查:')
            for status in icmp_status:
                output.append(f"  - {status}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取ICMP协议状态失败: {e}')
        return f'获取ICMP协议状态失败: {e}'
