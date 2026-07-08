import logging
import os
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_ldd_info.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_ldd_info')

def fetch_app_ldd_info(binary_path=None, check_missing=True):
    """
    采集程序动态链接库（指定程序的所有依赖so库/路径/版本/缺失检查）

    参数:
        binary_path: 可执行程序路径，如未指定则提示用户输入
        check_missing: 是否检查缺失的依赖库

    返回:
        格式化的动态链接库信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 动态链接库信息 ===')

        if not binary_path:
            output.append('错误: 请指定可执行程序路径')
            output.append('使用示例: fetch_app_ldd_info("/usr/bin/python3")')
            output.append('=====================')
            return '\n'.join(output)

        # 检查文件是否存在
        if not os.path.exists(binary_path):
            output.append(f'错误: 文件不存在: {binary_path}')
            output.append('=====================')
            return '\n'.join(output)

        # 检查是否是ELF文件
        if not is_elf_file(binary_path):
            output.append(f'错误: 文件不是ELF可执行文件: {binary_path}')
            output.append('=====================')
            return '\n'.join(output)

        # 获取动态链接库信息
        ldd_info = fetch_ldd_output(binary_path)

        if not ldd_info:
            output.append('未检测到动态链接库依赖')
        else:
            # 解析ldd输出
            dependencies = analyze_ldd_output(ldd_info)

            # 分类依赖库
            normal_deps = []
            missing_deps = []

            for dep in dependencies:
                if dep['status'] == '正常':
                    normal_deps.append(dep)
                else:
                    missing_deps.append(dep)

            # 显示正常依赖库
            if normal_deps:
                output.append(f"正常依赖库 ({len(normal_deps)}):")
                for dep in normal_deps[:15]:  # 最多显示15个
                    output.append(f"  - {dep['name']}")
                    output.append(f"    路径: {dep['path']}")
                    if dep['version']:
                        output.append(f"    版本: {dep['version']}")

                if len(normal_deps) > 15:
                    output.append(f"  ... 还有 {len(normal_deps) - 15} 个依赖库未显示 ...")

            # 显示缺失依赖库
            if missing_deps:
                output.append(f"\n缺失依赖库 ({len(missing_deps)}):")
                for dep in missing_deps:
                    output.append(f"  - {dep['name']}")
                    output.append(f"    状态: {dep['status']}")

            # 检查依赖库版本
            ver_data = verify_library_versions(normal_deps)
            if ver_data:
                output.append("\n依赖库版本信息:")
                for info in ver_data[:10]:  # 最多显示10个
                    output.append(f"  - {info}")
                if len(ver_data) > 10:
                    output.append(f"  ... 还有 {len(ver_data) - 10} 个版本信息未显示 ...")

        # 检查系统库路径
        lib_paths = fetch_system_lib_paths()
        output.append(f"\n系统库路径 ({len(lib_paths)}):")
        for path in lib_paths:
            output.append(f"  - {path}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取动态链接库信息失败: {e}')
        return f'获取动态链接库信息失败: {e}'
def is_elf_file(file_path):
    """
    检查文件是否是ELF文件
    """
    try:
        output = subprocess.run(['file', '-b', file_path], capture_output=True, text=True)
        return 'ELF' in output.stdout
    except Exception:
        return False
def fetch_ldd_output(binary_path):
    """
    获取ldd命令输出
    """
    try:
        output = subprocess.run(['ldd', binary_path], capture_output=True, text=True)
        if output.returncode == 0:
            return output.stdout
        return None
    except Exception:
        return None
def analyze_ldd_output(ldd_output):
    """
    解析ldd命令输出
    """
    dependencies = []
    lines = ldd_output.strip().split('\n')

    for line in lines:
        if not line.strip():
            continue

        parts = line.split()
        dep_info = {
            'name': '',
            'path': '',
            'version': '',
            'status': '正常'
        }

        if '=>' in line:
            # 正常依赖库
            if len(parts) >= 3:
                dep_info['name'] = parts[0]
                if parts[1] == '=>':
                    if parts[2] != 'not':
                        dep_info['path'] = parts[2]
                        # 尝试获取版本信息
                        if len(parts) > 3:
                            dep_info['version'] = ' '.join(parts[3:])
                    else:
                        dep_info['status'] = '缺失'
        else:
            # 特殊依赖（如linux-vdso.so）
            dep_info['name'] = parts[0]
            dep_info['path'] = parts[0]

        dependencies.append(dep_info)

    return dependencies
