import logging
import os
import re
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('net_hosts')

def fetch_net_hosts():
    """
    采集hosts配置（/etc/hosts/IP-主机名映射/注释/自定义解析规则）

    返回:
        格式化的hosts配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== hosts配置 ===')

        # 采集/etc/hosts文件内容
        hosts_content = load_hosts_file()
        if hosts_content:
            # 解析hosts文件
            parsed_hosts = analyze_hosts_file(hosts_content)

            # 显示hosts文件信息
            output.append('文件信息:')
            output.append(f"  文件路径: /etc/hosts")
            output.append(f"  文件大小: {os.path.getsize('/etc/hosts')} 字节")
            output.append(f"  最后修改时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime('/etc/hosts')))}")

            # 显示IP-主机名映射
            if parsed_hosts.get('entries'):
                output.append('\nIP-主机名映射:')
                for entry in parsed_hosts.get('entries'):
                    display_hosts_entry(output, entry)

            # 显示注释
            if parsed_hosts.get('comments'):
                output.append('\n注释:')
                for comment in parsed_hosts.get('comments'):
                    output.append(f"  - {comment}")

            # 显示自定义解析规则
            if parsed_hosts.get('custom_rules'):
                output.append('\n自定义解析规则:')
                for rule in parsed_hosts.get('custom_rules'):
                    output.append(f"  - {rule}")

            # 显示hosts文件统计
            hosts_stats = fetch_hosts_stats(parsed_hosts)
            if hosts_stats:
                output.append('\nhosts文件统计:')
                for key, value in hosts_stats.items():
                    output.append(f"  {key}: {value}")
        else:
            output.append('hosts文件不存在或为空')

        # 检查hosts文件权限
        hosts_permissions = verify_hosts_permissions()
        if hosts_permissions:
            output.append('\nhosts文件权限:')
            for key, value in hosts_permissions.items():
                output.append(f"  {key}: {value}")

        # 检查hosts文件格式
        hosts_format_check = verify_hosts_format()
        if hosts_format_check:
            output.append('\nhosts文件格式检查:')
            for check in hosts_format_check:
                output.append(f"  - {check}")

        # 检查hosts文件中的特殊条目
        special_entries = verify_special_entries()
        if special_entries:
            output.append('\n特殊条目:')
            for entry in special_entries:
                output.append(f"  - {entry}")

        # 显示采样时间
        output.append('\n采样时间:')
        output.append(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取hosts配置失败: {e}')
        return f'获取hosts配置失败: {e}'
def load_hosts_file():
    """
    读取/etc/hosts文件
    """
    try:
        with open('/etc/hosts', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f'读取hosts文件失败: {e}')
        return None
