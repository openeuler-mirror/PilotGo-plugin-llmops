import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_apt_list.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_apt_list')

def fetch_app_apt_list(apt_info=None):
    """
    采集APT包信息

    参数:
        apt_info: 信息类型，可选值：
            - 'all': 所有已安装DEB包
            - 'version': 版本信息
            - 'publisher': 发布者信息
            - 'time': 安装时间
            - None: 获取所有信息

    返回:
        格式化的APT包信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== APT包信息 ===')

        # 检查系统是否支持APT
        if not is_apt_based_system():
            return "当前系统不是基于APT的系统（如Ubuntu/Debian）"

        # 获取APT包信息
        apt_packages = fetch_apt_packages()

        # 根据参数返回不同信息
        if apt_info == 'all':
            if apt_packages:
                output.append(f"已安装DEB包数量: {len(apt_packages)}")
                output.append("\n部分DEB包信息（最多显示20个）:")
                for i, pkg in enumerate(apt_packages[:20]):
                    output.append(f"  {pkg['name']}={pkg['version']}")
                    output.append(f"    发布者: {pkg.get('publisher', 'Unknown')}")
                    output.append(f"    安装时间: {pkg.get('install_time', 'Unknown')}")
                if len(apt_packages) > 20:
                    output.append(f"\n... 还有 {len(apt_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的DEB包")
            output.append('=====================')
            return '\n'.join(output)
        elif apt_info == 'version':
            if apt_packages:
                versions = '\n'.join([f"  {pkg['name']}: {pkg['version']}" for pkg in apt_packages[:20]])
                output.append(f"版本信息（最多显示20个）:\n{versions}")
                if len(apt_packages) > 20:
                    output.append(f"\n... 还有 {len(apt_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的DEB包")
            output.append('=====================')
            return '\n'.join(output)
        elif apt_info == 'publisher':
            if apt_packages:
                publishers = {}
                for pkg in apt_packages:
                    publisher = pkg.get('publisher', 'Unknown')
                    if publisher not in publishers:
                        publishers[publisher] = 0
                    publishers[publisher] += 1
                output.append("发布者统计:")
                for publisher, count in publishers.items():
                    output.append(f"  {publisher}: {count}个包")
            else:
                output.append("未检测到已安装的DEB包")
            output.append('=====================')
            return '\n'.join(output)
        elif apt_info == 'time':
            if apt_packages:
                # 按安装时间排序
                sorted_packages = sorted(apt_packages, key=lambda x: x.get('install_time', ''), reverse=True)
                times = '\n'.join([f"  {pkg['name']}: {pkg.get('install_time', 'Unknown')}" for pkg in sorted_packages[:20]])
                output.append(f"安装时间（最多显示20个，按时间倒序）:\n{times}")
                if len(sorted_packages) > 20:
                    output.append(f"\n... 还有 {len(sorted_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的DEB包")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if apt_packages:
                output.append(f"已安装DEB包数量: {len(apt_packages)}")

                # 版本统计
                output.append("\n版本信息（部分）:")
                for pkg in apt_packages[:10]:
                    output.append(f"  {pkg['name']}: {pkg['version']}")

                # 发布者统计
                publishers = {}
                for pkg in apt_packages:
                    publisher = pkg.get('publisher', 'Unknown')
                    if publisher not in publishers:
                        publishers[publisher] = 0
                    publishers[publisher] += 1
                output.append("\n发布者统计:")
                for publisher, count in list(publishers.items())[:5]:
                    output.append(f"  {publisher}: {count}个包")

                # 安装时间
                sorted_packages = sorted(apt_packages, key=lambda x: x.get('install_time', ''), reverse=True)
                output.append("\n最近安装的包（部分）:")
                for pkg in sorted_packages[:5]:
                    output.append(f"  {pkg['name']}: {pkg.get('install_time', 'Unknown')}")

                if len(apt_packages) > 10:
                    output.append(f"\n... 还有 {len(apt_packages) - 10} 个包未显示 ...")
            else:
                output.append("未检测到已安装的DEB包")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取APT包信息失败: {e}')
        return f'获取APT包信息失败: {e}'
