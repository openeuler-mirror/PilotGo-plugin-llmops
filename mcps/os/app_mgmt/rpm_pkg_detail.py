import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.filepath.join(os.filepath.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.filepath.join(LOG_DIR, "app_rpm_info.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_rpm_info')

def fetch_app_rpm_info(package_name=None, info_type=None):
    """
    采集指定RPM包详情

    参数:
        package_name: 包名，如未指定则返回提示信息
        info_type: 信息类型，可选值：
            - 'dependencies': 包依赖
            - 'filepath': 安装路径
            - 'files': 文件列表
            - 'changes': 版本变更
            - 'signature': 签名信息
            - None: 获取所有信息

    返回:
        格式化的RPM包详细信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== RPM包详细信息 ===')

        # 检查系统是否支持RPM
        if not is_rpm_based_system():
            return "当前系统不是基于RPM的系统（如CentOS/RHEL/AlmaLinux）"

        # 检查是否指定了包名
        if not package_name:
            return "请指定要查询的RPM包名"

        # 检查包是否已安装
        if not is_package_installed(package_name):
            return f"RPM包 '{package_name}' 未安装"

        # 获取包详情
        package_info = fetch_package_details(package_name)

        # 根据参数返回不同信息
        if info_type == 'dependencies':
            deps = package_info.get('dependencies', '无依赖信息')
            if isinstance(deps, list):
                deps_list = '\n'.join([f"  {dep}" for dep in deps])
                return f"{package_name} 的依赖:\n{deps_list}"
            else:
                return f"{package_name} 的依赖: {deps}"
        elif info_type == 'filepath':
            filepath = package_info.get('installation_path', '无安装路径信息')
            return f"{package_name} 的安装路径: {filepath}"
        elif info_type == 'files':
            files = package_info.get('files', '无文件列表信息')
            if isinstance(files, list):
                files_list = '\n'.join([f"  {file}" for file in files[:20]])
                output = f"{package_name} 的文件列表（最多显示20个）:\n{files_list}"
                if len(files) > 20:
                    output += f"\n... 还有 {len(files) - 20} 个文件未显示 ..."
                return output
            else:
                return f"{package_name} 的文件列表: {files}"
        elif info_type == 'changes':
            changes = package_info.get('changes', '无版本变更信息')
            return f"{package_name} 的版本变更: {changes}"
        elif info_type == 'signature':
            signature = package_info.get('signature', '无签名信息')
            return f"{package_name} 的签名信息: {signature}"
        else:
            # 获取所有信息
            output.append(f"包名: {package_info.get('name', package_name)}")
            output.append(f"版本: {package_info.get('version', 'Unknown')}")
            output.append(f"发布版本: {package_info.get('release', 'Unknown')}")
            output.append(f"架构: {package_info.get('arch', 'Unknown')}")
            output.append(f"发布者: {package_info.get('vendor', 'Unknown')}")
            output.append(f"安装时间: {package_info.get('install_time', 'Unknown')}")

            # 包依赖
            deps = package_info.get('dependencies', [])
            if deps:
                output.append("\n依赖:")
                for dep in deps[:10]:
                    output.append(f"  {dep}")
                if len(deps) > 10:
                    output.append(f"  ... 还有 {len(deps) - 10} 个依赖未显示 ...")
            else:
                output.append("\n依赖: 无")

            # 安装路径
            filepath = package_info.get('installation_path', 'Unknown')
            output.append(f"\n安装路径: {filepath}")

            # 文件列表
            files = package_info.get('files', [])
            if files:
                output.append("\n文件列表（部分）:")
                for file in files[:10]:
                    output.append(f"  {file}")
                if len(files) > 10:
                    output.append(f"  ... 还有 {len(files) - 10} 个文件未显示 ...")
            else:
                output.append("\n文件列表: 无")

            # 版本变更
            changes = package_info.get('changes', '无')
            output.append(f"\n版本变更: {changes}")

            # 签名信息
            signature = package_info.get('signature', '无')
            output.append(f"\n签名信息: {signature}")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取RPM包详情失败: {e}')
        return f'获取RPM包详情失败: {e}'
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
        if os.filepath.exists('/etc/redhat-release'):
            return True

        # 检查系统类型
        distro = platform.platform().lower()
        return any(keyword in distro for keyword in ['centos', 'rhel', 'redhat', 'almalinux', 'fedora'])

    except Exception:
        return False
