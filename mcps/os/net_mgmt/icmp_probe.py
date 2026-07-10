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
def fetch_icmp_stats():
    """
    获取ICMP包收发数
    """
    stats = {}

    try:
        # 读取/proc/net/snmp
        with open('/proc/net/snmp', 'r') as f:
            lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    if parts[0] == 'Icmp:':
                        if len(parts) >= 11:
                            stats['ICMP接收包数'] = parts[1]
                            stats['ICMP发送包数'] = parts[7]
                            stats['ICMP接收错误数'] = parts[2]
                            stats['ICMP发送错误数'] = parts[8]
                            stats['ICMP接收目标不可达数'] = parts[3]
                            stats['ICMP发送目标不可达数'] = parts[9]
                            stats['ICMP接收超时数'] = parts[4]
                            stats['ICMP发送超时数'] = parts[10]
                    elif parts[0] == 'IcmpMsg:':
                        if len(parts) >= 21:
                            stats['ICMP消息类型统计'] = {
                                'EchoRequests': parts[1],
                                'EchoReplies': parts[2],
                                'DestUnreachs': parts[3],
                                'TimeExcds': parts[4],
                                'ParamProbs': parts[5],
                                'SrcQuenchs': parts[6],
                                'Redirects': parts[7],
                                'RouterAdverts': parts[8],
                                'RouterSolicits': parts[9],
                                'TStampRequests': parts[10],
                                'TStampReplies': parts[11],
                                'IcmpMaskRequests': parts[12],
                                'IcmpMaskReplies': parts[13]
                            }

    except Exception as e:
        logger.error(f'获取ICMP包收发数失败: {e}')

    return stats
def fetch_icmp_rates(icmp_stats):
    """
    计算ICMP包丢包率和错包率
    """
    rates = {}

    try:
        if icmp_stats:
            # 计算丢包率
            if 'ICMP接收包数' in icmp_stats and 'ICMP发送包数' in icmp_stats:
                received = int(icmp_stats['ICMP接收包数'])
                sent = int(icmp_stats['ICMP发送包数'])
                if sent > 0:
                    loss_rate = ((sent - received) / sent) * 100
                    rates['ICMP丢包率'] = f"{loss_rate:.2f}%"

            # 计算错包率
            if 'ICMP接收错误数' in icmp_stats and 'ICMP接收包数' in icmp_stats:
                errors = int(icmp_stats['ICMP接收错误数'])
                received = int(icmp_stats['ICMP接收包数'])
                if received > 0:
                    error_rate = (errors / received) * 100
                    rates['ICMP错包率'] = f"{error_rate:.2f}%"

    except Exception as e:
        logger.error(f'计算ICMP包率失败: {e}')

    return rates
