import json
import logging
import os
import platform
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_npm_list.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_npm_list')

def fetch_app_npm_list(npm_info=None, scope=None):
    """
    采集Node.js NPM包

    参数:
        npm_info: 信息类型，可选值：
            - 'all': 所有已安装NPM包
            - 'version': 版本信息
            - 'dependencies': 依赖信息
            - 'path': 安装路径
            - None: 获取所有信息
        scope: 作用域，可选值：
            - 'global': 全局NPM包
            - 'local': 项目级NPM包
            - None: 所有NPM包

    返回:
        格式化的NPM包信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== Node.js NPM包信息 ===')

        # 检查系统是否安装了npm
        if not is_npm_available():
            return "当前系统未安装Node.js NPM包管理器"

        # 获取NPM包信息
        npm_packages = fetch_npm_packages(scope)

        # 根据参数返回不同信息
        if npm_info == 'all':
            if npm_packages:
                output.append(f"已安装NPM包数量: {len(npm_packages)}")
                output.append("\n部分NPM包信息（最多显示20个）:")
                for i, pkg in enumerate(npm_packages[:20]):
                    output.append(f"  {pkg['name']}@{pkg['version']}")
                    output.append(f"    作用域: {pkg['scope']}")
                    output.append(f"    安装路径: {pkg['location']}")
                if len(npm_packages) > 20:
                    output.append(f"\n... 还有 {len(npm_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的NPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif npm_info == 'version':
            if npm_packages:
                versions = '\n'.join([f"  {pkg['name']}: {pkg['version']} ({pkg['scope']})" for pkg in npm_packages[:20]])
                output.append(f"版本信息（最多显示20个）:\n{versions}")
                if len(npm_packages) > 20:
                    output.append(f"\n... 还有 {len(npm_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的NPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif npm_info == 'dependencies':
            if npm_packages:
                output.append("依赖信息（部分）:")
                for pkg in npm_packages[:10]:
                    deps = pkg.get('dependencies', '无依赖信息')
                    if deps:
                        deps_str = ', '.join(list(deps.keys())[:5])
                        if len(deps) > 5:
                            deps_str += f"... 还有 {len(deps) - 5} 个依赖"
                    else:
                        deps_str = '无依赖'
                    output.append(f"  {pkg['name']}: {deps_str}")
            else:
                output.append("未检测到已安装的NPM包")
            output.append('=====================')
            return '\n'.join(output)
        elif npm_info == 'path':
            if npm_packages:
                output.append("安装路径（部分）:")
                for pkg in npm_packages[:20]:
                    output.append(f"  {pkg['name']}: {pkg['location']} ({pkg['scope']})")
                if len(npm_packages) > 20:
                    output.append(f"\n... 还有 {len(npm_packages) - 20} 个包未显示 ...")
            else:
                output.append("未检测到已安装的NPM包")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if npm_packages:
                output.append(f"已安装NPM包数量: {len(npm_packages)}")

                # 版本统计
                output.append("\n版本信息（部分）:")
                for pkg in npm_packages[:10]:
                    output.append(f"  {pkg['name']}: {pkg['version']} ({pkg['scope']})")

                # 作用域统计
                scopes = {}
                for pkg in npm_packages:
                    scope_key = pkg['scope']
                    if scope_key not in scopes:
                        scopes[scope_key] = 0
                    scopes[scope_key] += 1
                output.append("\n作用域统计:")
                for scope_key, count in scopes.items():
                    output.append(f"  {scope_key}: {count}个包")

                # 安装路径
                locations = {}
                for pkg in npm_packages:
                    location = pkg['location']
                    if location not in locations:
                        locations[location] = 0
                    locations[location] += 1
                output.append("\n安装路径统计:")
                for location, count in list(locations.items())[:5]:
                    output.append(f"  {location}: {count}个包")

                if len(npm_packages) > 10:
                    output.append(f"\n... 还有 {len(npm_packages) - 10} 个包未显示 ...")
            else:
                output.append("未检测到已安装的NPM包")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取NPM包信息失败: {e}')
        return f'获取NPM包信息失败: {e}'
def is_npm_available():
    """
    检查系统是否安装了npm

    返回:
        bool: 是否安装了npm
    """
    try:
        # 检查是否存在npm命令
        output = subprocess.run(['which', 'npm'], capture_output=True, text=True)
        if output.returncode == 0:
            return True

        return False

    except Exception:
        return False
