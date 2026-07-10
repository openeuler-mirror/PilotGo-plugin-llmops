import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_rpm_list.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_rpm_list')

def fetch_app_rpm_list(rpm_info=None):
    """
    采集RPM包信息

    参数:
        rpm_info: 信息类型，可选值：
            - 'all': 所有已安装RPM包
            - 'version': 版本信息
            - 'publisher': 发布者信息
            - 'time': 安装时间
            - None: 获取所有信息

    返回:
        格式化的RPM包信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== RPM包信息 ===')

        # 检查系统是否支持RPM
        if not is_rpm_based_system():
            return "当前系统不是基于RPM的系统（如CentOS/RHEL/AlmaLinux）"

        # 获取RPM包信息
        rpm_packages = fetch_rpm_packages()

        # 根据参数返回不同信息
        if rpm_info == 'all':
            if rpm_packages:
                output.append(f"已安装RPM包数量: {len(rpm_packages)}")
                output.append("\n部分RPM包信息（最多显示20个）:")
                for i, pkg in enumerate(rpm_packages[:20]):
                    output.append(f"  {pkg['name']}-{pkg['version']}-{pkg['release']} ({pkg['arch']})")
                    output.append(f"    发布者: {pkg['vendor']}")
                    output.append(f"    安装时间: {pkg['install_time']}")
                if len(rpm_packages) > 20:
                    output.append(f"\n... 还有 {len(rpm_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的RPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif rpm_info == 'version':
            if rpm_packages:
                versions = '\n'.join([f"  {pkg['name']}: {pkg['version']}-{pkg['release']}" for pkg in rpm_packages[:20]])
                output.append(f"版本信息（最多显示20个）:\n{versions}")
                if len(rpm_packages) > 20:
                    output.append(f"\n... 还有 {len(rpm_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的RPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif rpm_info == 'publisher':
            if rpm_packages:
                publishers = {}
                for pkg in rpm_packages:
                    vendor = pkg['vendor']
                    if vendor not in publishers:
                        publishers[vendor] = 0
                    publishers[vendor] += 1
                output.append("发布者统计:")
                for vendor, count in publishers.items():
                    output.append(f"  {vendor}: {count}个包")
            else:
                output.append("未检测到已安装的RPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif rpm_info == 'time':
            if rpm_packages:
                # 按安装时间排序
                sorted_packages = sorted(rpm_packages, key=lambda x: x['install_time'], reverse=True)
                times = '\n'.join([f"  {pkg['name']}: {pkg['install_time']}" for pkg in sorted_packages[:20]])
                output.append(f"安装时间（最多显示20个，按时间倒序）:\n{times}")
                if len(sorted_packages) > 20:
                    output.append(f"\n... 还有 {len(sorted_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的RPM包")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if rpm_packages:
                output.append(f"已安装RPM包数量: {len(rpm_packages)}")

                # 版本统计
                output.append("\n版本信息（部分）:")
                for pkg in rpm_packages[:10]:
                    output.append(f"  {pkg['name']}: {pkg['version']}-{pkg['release']}")

                # 发布者统计
                publishers = {}
                for pkg in rpm_packages:
                    vendor = pkg['vendor']
                    if vendor not in publishers:
                        publishers[vendor] = 0
                    publishers[vendor] += 1
                output.append("\n发布者统计:")
                for vendor, count in list(publishers.items())[:5]:
                    output.append(f"  {vendor}: {count}个包")

                # 安装时间
                sorted_packages = sorted(rpm_packages, key=lambda x: x['install_time'], reverse=True)
                output.append("\n最近安装的包（部分）:")
                for pkg in sorted_packages[:5]:
                    output.append(f"  {pkg['name']}: {pkg['install_time']}")

                if len(rpm_packages) > 10:
                    output.append(f"\n... 还有 {len(rpm_packages) - 10} 个包未显示 ...")
            else:
                output.append("未检测到已安装的RPM包")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取RPM包信息失败: {e}')
        return f'获取RPM包信息失败: {e}'
def is_rpm_based_system():
    """
    检查系统是否是基于RPM的系统

    返回:
        bool: 是否是基于RPM的系统
    """
    try:
        # 检查是否存在rpm命令
        output = subprocess.run(['which', 'rpm'], capture_output=True, text=True)
        if output.returncode == 0:
            return True

        # 检查系统发行版
        if os.path.exists('/etc/redhat-release'):
            return True

        # 检查系统类型
        distro = platform.platform().lower()
        return any(keyword in distro for keyword in ['centos', 'rhel', 'redhat', 'almalinux', 'fedora'])

    except Exception:
        return False
def fetch_rpm_packages():
    """
    获取所有已安装的RPM包

    返回:
        RPM包信息列表
    """
    try:
        packages = []

        # 使用rpm命令获取所有已安装的包
        output = subprocess.run(['rpm', '-qa', '--queryformat', '%{NAME}\t%{VERSION}\t%{RELEASE}\t%{ARCH}\t%{VENDOR}\t%{INSTALLTIME:date}\n'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        pkg_info = {
                            'name': parts[0],
                            'version': parts[1],
                            'release': parts[2],
                            'arch': parts[3],
                            'vendor': parts[4],
                            'install_time': parts[5]
                        }
                        packages.append(pkg_info)

        return packages

    except Exception as e:
        logger.error(f'获取RPM包列表失败: {e}')
        return []

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_app_rpm_list",
    "function": fetch_app_rpm_list,
    "description": "采集RPM包信息（CentOS/RHEL/AlmaLinux，所有已安装RPM包/版本/发布者/安装时间）",
    "parameters": {
        "type": "object",
        "properties": {
            "rpm_info": {
                "type": "string",
                "description": "信息类型，可选值：all（所有已安装RPM包）、version（版本信息）、publisher（发布者信息）、time（安装时间），不指定则获取所有信息",
                "enum": ["all", "version", "publisher", "time"]
            }
        },
        "required": []
    }
}
