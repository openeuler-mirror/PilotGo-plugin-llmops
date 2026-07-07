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
