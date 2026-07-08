import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_flatpak_list.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_flatpak_list')

def fetch_app_flatpak_list(flatpak_info=None):
    """
    采集Flatpak包信息

    参数:
        flatpak_info: 信息类型，可选值：
            - 'all': 所有已安装Flatpak包
            - 'version': 版本信息
            - 'remote': 远程仓库信息
            - 'state': 运行状态
            - None: 获取所有信息

    返回:
        格式化的Flatpak包信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== Flatpak包信息 ===')

        # 检查系统是否支持Flatpak
        if not is_flatpak_available():
            return "当前系统未安装Flatpak包管理器"

        # 获取Flatpak包信息
        flatpak_packages = fetch_flatpak_packages()

        # 根据参数返回不同信息
        if flatpak_info == 'all':
            if flatpak_packages:
                output.append(f"已安装Flatpak包数量: {len(flatpak_packages)}")
                output.append("\n部分Flatpak包信息（最多显示20个）:")
                for i, pkg in enumerate(flatpak_packages[:20]):
                    output.append(f"  {pkg['name']} ({pkg['version']})")
                    output.append(f"    应用ID: {pkg['app_id']}")
                    output.append(f"    远程仓库: {pkg['remote']}")
                    output.append(f"    运行状态: {pkg['state']}")
                if len(flatpak_packages) > 20:
                    output.append(f"\n... 还有 {len(flatpak_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Flatpak包")
            output.append('=====================')
            return '\n'.join(output)
        elif flatpak_info == 'version':
            if flatpak_packages:
                versions = '\n'.join([f"  {pkg['name']}: {pkg['version']}" for pkg in flatpak_packages[:20]])
                output.append(f"版本信息（最多显示20个）:\n{versions}")
                if len(flatpak_packages) > 20:
                    output.append(f"\n... 还有 {len(flatpak_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Flatpak包")
            output.append('=====================')
            return '\n'.join(output)
        elif flatpak_info == 'remote':
            if flatpak_packages:
                remotes = {}
                for pkg in flatpak_packages:
                    remote = pkg['remote']
                    if remote not in remotes:
                        remotes[remote] = []
                    remotes[remote].append(pkg['name'])
                output.append("远程仓库统计:")
                for remote, packages in remotes.items():
                    output.append(f"  {remote}: {len(packages)}个包")
                    output.append(f"    包列表: {', '.join(packages[:5])}")
                    if len(packages) > 5:
                        output.append(f"    ... 还有 {len(packages) - 5} 个包")
            else:
                output.append("未检测到已安装的Flatpak包")
            output.append('=====================')
            return '\n'.join(output)
        elif flatpak_info == 'state':
            if flatpak_packages:
                statuses = {}
                for pkg in flatpak_packages:
                    state = pkg['state']
                    if state not in statuses:
                        statuses[state] = []
                    statuses[state].append(pkg['name'])
                output.append("运行状态统计:")
                for state, packages in statuses.items():
                    output.append(f"  {state}: {', '.join(packages[:5])}")
                    if len(packages) > 5:
                        output.append(f"    ... 还有 {len(packages) - 5} 个包")
            else:
                output.append("未检测到已安装的Flatpak包")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if flatpak_packages:
                output.append(f"已安装Flatpak包数量: {len(flatpak_packages)}")

                # 版本统计
                output.append("\n版本信息（部分）:")
                for pkg in flatpak_packages[:10]:
                    output.append(f"  {pkg['name']}: {pkg['version']}")

                # 远程仓库统计
                remotes = {}
                for pkg in flatpak_packages:
                    remote = pkg['remote']
                    if remote not in remotes:
                        remotes[remote] = 0
                    remotes[remote] += 1
                output.append("\n远程仓库统计:")
                for remote, count in list(remotes.items())[:5]:
                    output.append(f"  {remote}: {count}个包")

                # 运行状态
                statuses = {}
                for pkg in flatpak_packages:
                    state = pkg['state']
                    if state not in statuses:
                        statuses[state] = []
                    statuses[state].append(pkg['name'])
                output.append("\n运行状态:")
                for state, packages in statuses.items():
                    output.append(f"  {state}: {len(packages)}个包")

                if len(flatpak_packages) > 10:
                    output.append(f"\n... 还有 {len(flatpak_packages) - 10} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Flatpak包")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Flatpak包信息失败: {e}')
        return f'获取Flatpak包信息失败: {e}'
