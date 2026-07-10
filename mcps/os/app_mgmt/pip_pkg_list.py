import json
import logging
import os
import platform
import subprocess
import sys

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_pip_list.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_pip_list')

def fetch_app_pip_list(pip_info=None, scope=None):
    """
    采集Python Pip包

    参数:
        pip_info: 信息类型，可选值：
            - 'all': 所有已安装Pip包
            - 'version': 版本信息
            - 'dependencies': 依赖信息
            - 'path': 安装路径
            - None: 获取所有信息
        scope: 作用域，可选值：
            - 'system': 系统级Pip包
            - 'user': 用户级Pip包
            - None: 所有Pip包

    返回:
        格式化的Pip包信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== Python Pip包信息 ===')

        # 检查系统是否安装了pip
        pip_commands = fetch_available_pip_commands()
        if not pip_commands:
            return "当前系统未安装Python Pip包管理器"

        # 获取Pip包信息
        pip_packages = fetch_pip_packages(scope)

        # 根据参数返回不同信息
        if pip_info == 'all':
            if pip_packages:
                output.append(f"已安装Pip包数量: {len(pip_packages)}")
                output.append("\n部分Pip包信息（最多显示20个）:")
                for i, pkg in enumerate(pip_packages[:20]):
                    output.append(f"  {pkg['name']}-{pkg['version']}")
                    output.append(f"    作用域: {pkg['scope']}")
                    output.append(f"    安装路径: {pkg['location']}")
                if len(pip_packages) > 20:
                    output.append(f"\n... 还有 {len(pip_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Pip包")
            output.append('=====================')
            return '\n'.join(output)
        elif pip_info == 'version':
            if pip_packages:
                versions = '\n'.join([f"  {pkg['name']}: {pkg['version']} ({pkg['scope']})" for pkg in pip_packages[:20]])
                output.append(f"版本信息（最多显示20个）:\n{versions}")
                if len(pip_packages) > 20:
                    output.append(f"\n... 还有 {len(pip_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Pip包")
            output.append('=====================')
            return '\n'.join(output)
        elif pip_info == 'dependencies':
            if pip_packages:
                output.append("依赖信息（部分）:")
                for pkg in pip_packages[:10]:
                    deps = pkg.get('dependencies', '无依赖信息')
                    if deps:
                        deps_str = ', '.join(deps[:5])
                        if len(deps) > 5:
                            deps_str += f"... 还有 {len(deps) - 5} 个依赖"
                    else:
                        deps_str = '无依赖'
                    output.append(f"  {pkg['name']}: {deps_str}")
            else:
                output.append("未检测到已安装的Pip包")
            output.append('=====================')
            return '\n'.join(output)
        elif pip_info == 'path':
            if pip_packages:
                output.append("安装路径（部分）:")
                for pkg in pip_packages[:20]:
                    output.append(f"  {pkg['name']}: {pkg['location']} ({pkg['scope']})")
                if len(pip_packages) > 20:
                    output.append(f"\n... 还有 {len(pip_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Pip包")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if pip_packages:
                output.append(f"已安装Pip包数量: {len(pip_packages)}")

                # 版本统计
                output.append("\n版本信息（部分）:")
                for pkg in pip_packages[:10]:
                    output.append(f"  {pkg['name']}: {pkg['version']} ({pkg['scope']})")

                # 作用域统计
                scopes = {}
                for pkg in pip_packages:
                    scope_key = pkg['scope']
                    if scope_key not in scopes:
                        scopes[scope_key] = 0
                    scopes[scope_key] += 1
                output.append("\n作用域统计:")
                for scope_key, count in scopes.items():
                    output.append(f"  {scope_key}: {count}个包")

                # 安装路径
                locations = {}
                for pkg in pip_packages:
                    location = pkg['location']
                    if location not in locations:
                        locations[location] = 0
                    locations[location] += 1
                output.append("\n安装路径统计:")
                for location, count in list(locations.items())[:5]:
                    output.append(f"  {location}: {count}个包")

                if len(pip_packages) > 10:
                    output.append(f"\n... 还有 {len(pip_packages) - 10} 个包未显示 ...")
            else:
                output.append("未检测到已安装的Pip包")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Pip包信息失败: {e}')
        return f'获取Pip包信息失败: {e}'
def fetch_available_pip_commands():
    """
    获取可用的pip命令

    返回:
        可用的pip命令列表
    """
    try:
        pip_commands = []

        # 检查常见的pip命令
        for cmd in ['pip3', 'pip', 'pip2']:
            output = subprocess.run(['which', cmd], capture_output=True, text=True)
            if output.returncode == 0:
                pip_commands.append(cmd)

        return pip_commands

    except Exception:
        return []
def fetch_pip_packages(scope=None):
    """
    获取所有已安装的Pip包

    参数:
        scope: 作用域，可选值：system, user, None

    返回:
        Pip包信息列表
    """
    try:
        packages = []
        pip_commands = fetch_available_pip_commands()

        for pip_cmd in pip_commands:
            # 获取系统级包
            if scope in [None, 'system']:
                system_packages = fetch_packages_with_command(pip_cmd, '--system')
                packages.extend(system_packages)

            # 获取用户级包
            if scope in [None, 'user']:
                user_packages = fetch_packages_with_command(pip_cmd, '--user')
                packages.extend(user_packages)

        return packages

    except Exception as e:
        logger.error(f'获取Pip包列表失败: {e}')
        return []
def fetch_packages_with_command(pip_cmd, user_flag=None):
    """
    使用指定的pip命令获取包信息

    参数:
        pip_cmd: pip命令
        user_flag: 用户标志

    返回:
        Pip包信息列表
    """
    try:
        packages = []

        # 构建命令
        cmd = [pip_cmd, 'list', '--format=json']
        if user_flag:
            cmd.append(user_flag)

        # 执行命令
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if output.returncode == 0:
            try:
                pkg_list = json.loads(output.stdout)
                for pkg in pkg_list:
                    pkg_info = {
                        'name': pkg.get('name'),
                        'version': pkg.get('version'),
                        'scope': 'user' if user_flag == '--user' else 'system',
                        'location': fetch_package_location(pip_cmd, pkg.get('name')),
                        'dependencies': fetch_package_dependencies(pip_cmd, pkg.get('name'))
                    }
                    packages.append(pkg_info)
            except json.JSONDecodeError:
                pass

        return packages

    except Exception as e:
        logger.error(f'使用{pip_cmd}获取包信息失败: {e}')
        return []
