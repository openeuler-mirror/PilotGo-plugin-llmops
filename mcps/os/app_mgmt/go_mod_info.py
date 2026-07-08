import json
import logging
import os
import platform
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_go_mod.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_go_mod')

def fetch_app_go_mod(mod_info=None):
    """
    采集Go模块信息

    参数:
        mod_info: 信息类型，可选值：
            - 'version': Go版本信息
            - 'dependencies': 依赖模块信息
            - 'paths': 下载地址信息
            - None: 获取所有信息

    返回:
        格式化的Go模块信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== Go模块信息 ===')

        # 检查系统是否安装了go
        if not is_go_available():
            return "当前系统未安装Go语言"

        # 获取Go模块信息
        go_info = fetch_go_module_info()

        # 根据参数返回不同信息
        if mod_info == 'version':
            return f"当前Go版本: {go_info['go_version']}" if 'go_version' in go_info else "未检测到Go版本信息"
        elif mod_info == 'dependencies':
            if 'dependencies' in go_info:
                deps = go_info['dependencies']
                if deps:
                    output.append(f"依赖模块数量: {len(deps)}")
                    output.append("\n部分依赖模块（最多显示20个）:")
                    for i, dep in enumerate(deps[:20]):
                        output.append(f"  {dep['path']} v{dep['version']}")
                    if len(deps) > 20:
                        output.append(f"\n... 还有 {len(deps) - 20} 个依赖模块未显示 ...")
                else:
                    output.append("未检测到依赖模块")
            else:
                output.append("未检测到依赖模块信息")
            output.append('=====================')
            return '\n'.join(output)
        elif mod_info == 'paths':
            if 'dependencies' in go_info:
                deps = go_info['dependencies']
                if deps:
                    output.append("依赖模块下载地址（部分）:")
                    for i, dep in enumerate(deps[:20]):
                        output.append(f"  {dep['path']}: {dep.get('download_url', 'Unknown')}")
                    if len(deps) > 20:
                        output.append(f"\n... 还有 {len(deps) - 20} 个依赖模块未显示 ...")
                else:
                    output.append("未检测到依赖模块")
            else:
                output.append("未检测到依赖模块信息")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if 'go_version' in go_info:
                output.append(f"Go版本: {go_info['go_version']}")
            else:
                output.append("Go版本: 未知")

            if 'module' in go_info:
                output.append(f"当前模块: {go_info['module']}")
            else:
                output.append("当前模块: 未知")

            if 'dependencies' in go_info:
                deps = go_info['dependencies']
                output.append(f"依赖模块数量: {len(deps)}")

                if deps:
                    output.append("\n部分依赖模块（最多显示10个）:")
                    for i, dep in enumerate(deps[:10]):
                        output.append(f"  {dep['path']} v{dep['version']}")
                        if 'download_url' in dep:
                            output.append(f"    下载地址: {dep['download_url']}")

                    if len(deps) > 10:
                        output.append(f"\n... 还有 {len(deps) - 10} 个依赖模块未显示 ...")
                else:
                    output.append("\n依赖模块: 无")
            else:
                output.append("\n依赖模块: 未检测到")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Go模块信息失败: {e}')
        return f'获取Go模块信息失败: {e}'
def is_go_available():
    """
    检查系统是否安装了go

    返回:
        bool: 是否安装了go
    """
    try:
        # 检查是否存在go命令
        output = subprocess.run(['which', 'go'], capture_output=True, text=True)
        if output.returncode == 0:
            return True

        return False

    except Exception:
        return False
def fetch_go_module_info():
    """
    获取Go模块信息

    返回:
        Go模块信息字典
    """
    try:
        details = {}

        # 获取Go版本
        go_version = fetch_go_version()
        if go_version:
            details['go_version'] = go_version

        # 检查当前目录是否有go.mod文件
        if os.path.exists('go.mod'):
            # 获取模块信息
            mod_info = fetch_module_info()
            if mod_info:
                details.update(mod_info)
        else:
            details['module'] = '当前目录不是Go项目（无go.mod文件）'
            details['dependencies'] = []

        return details

    except Exception as e:
        logger.error(f'获取Go模块信息失败: {e}')
        return {'go_version': fetch_go_version(), 'module': '获取模块信息失败', 'dependencies': []}
def fetch_go_version():
    """
    获取Go版本

    返回:
        Go版本字符串
    """
    try:
        output = subprocess.run(['go', 'version'], capture_output=True, text=True)

        if output.returncode == 0:
            output = output.stdout.strip()
            # 解析版本号
            parts = output.split(' ')
            if len(parts) >= 3:
                return parts[2]

        return 'Unknown'

    except Exception:
        return 'Unknown'
def fetch_module_info():
    """
    获取模块信息

    返回:
        模块信息字典
    """
    try:
        details = {}

        # 获取模块路径
        output = subprocess.run(['go', 'list', '-m'], capture_output=True, text=True)

        if output.returncode == 0:
            details['module'] = output.stdout.strip()

        # 获取依赖信息
        dependencies = fetch_dependencies()
        if dependencies:
            details['dependencies'] = dependencies
        else:
            details['dependencies'] = []

        return details

    except Exception as e:
        logger.error(f'获取模块信息失败: {e}')
        return {'module': 'Unknown', 'dependencies': []}
def fetch_dependencies():
    """
    获取依赖信息

    返回:
        依赖信息列表
    """
    try:
        dependencies = []

        # 使用go mod graph获取依赖
        output = subprocess.run(['go', 'mod', 'graph'], capture_output=True, text=True)

        if output.returncode == 0:
            lines = output.stdout.strip().split('\n')
            dep_paths = set()

            for line in lines:
                parts = line.split(' ')
                if len(parts) == 2:
                    dep = parts[1]
                    # 解析依赖路径和版本
                    if '@' in dep:
                        path, version = dep.split('@', 1)
                        if path not in dep_paths:
                            dep_paths.add(path)
                            dependencies.append({
                                'path': path,
                                'version': version,
                                'download_url': fetch_download_url(path)
                            })

        return dependencies

    except Exception as e:
        logger.error(f'获取依赖信息失败: {e}')
        return []
def fetch_download_url(module_path):
    """
    获取模块下载地址

    参数:
        module_path: 模块路径

    返回:
        下载地址
    """
    try:
        return f"https://{module_path}"

    except Exception:
        return 'Unknown'

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_app_go_mod",
    "function": fetch_app_go_mod,
    "description": "采集Go模块信息（当前项目Go版本/依赖模块/版本/下载地址）",
    "parameters": {
        "type": "object",
        "properties": {
            "mod_info": {
                "type": "string",
                "description": "信息类型，可选值：version（Go版本信息）、dependencies（依赖模块信息）、paths（下载地址信息），不指定则获取所有信息",
                "enum": ["version", "dependencies", "paths"]
            }
        },
        "required": []
    }
}
