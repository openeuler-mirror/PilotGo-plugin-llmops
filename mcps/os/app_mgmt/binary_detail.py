from datetime import datetime
import hashlib
import logging
import os
import re
import subprocess

import stat

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_binary_info.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_binary_info')

def fetch_app_binary_info(binary_path=None):
    """
    采集可执行程序信息（程序路径/编译架构/依赖库/编译时间/权限）

    参数:
        binary_path: 可执行程序路径，如未指定则提示用户输入

    返回:
        格式化的可执行程序信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 可执行程序信息 ===')

        if not binary_path:
            output.append('错误: 请指定可执行程序路径')
            output.append('使用示例: fetch_app_binary_info("/usr/bin/python3")')
            output.append('=====================')
            return '\n'.join(output)

        # 检查文件是否存在
        if not os.path.exists(binary_path):
            output.append(f'错误: 文件不存在: {binary_path}')
            output.append('=====================')
            return '\n'.join(output)

        # 检查文件是否可执行
        if not os.access(binary_path, os.X_OK):
            output.append(f'警告: 文件不可执行: {binary_path}')

        # 获取文件基本信息
        output.append(f"程序路径: {binary_path}")

        # 获取文件权限
        perm_info = fetch_file_permissions(binary_path)
        output.append(f"文件权限: {perm_info}")

        # 获取文件大小
        file_size = os.path.getsize(binary_path)
        output.append(f"文件大小: {render_file_size(file_size)}")

        # 获取修改时间
        mtime = os.path.getmtime(binary_path)
        modify_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        output.append(f"修改时间: {modify_time}")

        # 获取文件类型
        file_type = fetch_file_type(binary_path)
        output.append(f"文件类型: {file_type}")

        # 获取编译架构
        arch_info = fetch_binary_architecture(binary_path)
        output.append(f"编译架构: {arch_info}")

        # 获取依赖库
        dependencies = fetch_binary_dependencies(binary_path)
        if dependencies:
            output.append("依赖库:")
            for dep in dependencies[:10]:  # 最多显示10个依赖
                output.append(f"  - {dep}")
            if len(dependencies) > 10:
                output.append(f"  ... 还有 {len(dependencies) - 10} 个依赖库未显示 ...")
        else:
            output.append("依赖库: 无")

        # 获取编译时间（如果是ELF文件）
        build_time = fetch_build_time(binary_path)
        if build_time:
            output.append(f"编译时间: {build_time}")

        # 获取文件哈希值
        hash_info = fetch_file_hash(binary_path)
        if hash_info:
            output.append(f"文件哈希: {hash_info}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取可执行程序信息失败: {e}')
        return f'获取可执行程序信息失败: {e}'
def fetch_file_permissions(file_path):
    """
    获取文件权限
    """
    try:
        st = os.stat(file_path)
        mode = st.st_mode
        permissions = stat.filemode(mode)
        return permissions
    except Exception:
        return '未知'
def render_file_size(size_in_bytes):
    """
    格式化文件大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"
def fetch_file_type(file_path):
    """
    获取文件类型
    """
    try:
        output = subprocess.run(['file', file_path], capture_output=True, text=True)
        if output.returncode == 0:
            return output.stdout.strip().split(':', 1)[1].strip()
        return '未知'
    except Exception:
        return '未知'
def fetch_binary_architecture(file_path):
    """
    获取二进制文件架构
    """
    try:
        output = subprocess.run(['file', '-b', file_path], capture_output=True, text=True)
        if output.returncode == 0:
            output = output.stdout.strip()
            if '64-bit' in output:
                return '64位'
            elif '32-bit' in output:
                return '32位'
            return output
        return '未知'
    except Exception:
        return '未知'
def fetch_binary_dependencies(file_path):
    """
    获取二进制文件依赖库
    """
    dependencies = []
    try:
        # 检查是否是ELF文件
        output = subprocess.run(['file', '-b', file_path], capture_output=True, text=True)
        if 'ELF' not in output.stdout:
            return dependencies

        # 使用ldd获取依赖
        ldd_result = subprocess.run(['ldd', file_path], capture_output=True, text=True)
        if ldd_result.returncode == 0:
            lines = ldd_result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        lib_name = parts[0]
                        lib_path = parts[2]
                        dependencies.append(f"{lib_name} ({lib_path})")
                    else:
                        dependencies.append(line.strip())
    except Exception:
        pass
    return dependencies
def fetch_build_time(file_path):
    """
    获取二进制文件编译时间
    """
    try:
        # 检查是否是ELF文件
        output = subprocess.run(['file', '-b', file_path], capture_output=True, text=True)
        if 'ELF' not in output.stdout:
            return None

        # 使用readelf获取编译时间
        readelf_result = subprocess.run(['readelf', '-h', file_path], capture_output=True, text=True)
        if readelf_result.returncode == 0:
            for line in readelf_result.stdout.split('\n'):
                if 'Build ID:' in line:
                    return line.strip().split(':', 1)[1].strip()

        # 尝试使用strings查找时间戳
        strings_result = subprocess.run(['strings', file_path], capture_output=True, text=True)
        if strings_result.returncode == 0:
            # 查找类似编译时间的字符串
            time_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
            matches = re.findall(time_pattern, strings_result.stdout)
            if matches:
                return matches[0]
    except Exception:
        pass
    return None
def fetch_file_hash(file_path):
    """
    获取文件哈希值
    """
    try:
        hasher = hashlib.sha512()
        with open(file_path, 'rb') as f:
            buf = f.read(65536)
            while buf:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return None

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_app_binary_info",
    "function": fetch_app_binary_info,
    "description": "采集可执行程序信息（程序路径/编译架构/依赖库/编译时间/权限）",
    "parameters": {
        "type": "object",
        "properties": {
            "binary_path": {
                "type": "string",
                "description": "可执行程序路径"
            }
        },
        "required": ["binary_path"]
    }
}
