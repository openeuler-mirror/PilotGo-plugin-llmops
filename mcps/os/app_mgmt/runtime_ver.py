import logging
import os
import platform
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_runtime_version.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_runtime_version')

def fetch_app_runtime_version(runtime_type=None):
    """
    采集运行时版本（Python/Java/Go/Node.js/PHP/Redis/MongoDB等版本）

    参数:
        runtime_type: 运行时类型，如未指定则获取所有支持的运行时版本

    返回:
        格式化的运行时版本信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 运行时版本信息 ===')

        # 支持的运行时类型
        runtime_types = {
            'python': fetch_python_version,
            'java': fetch_java_version,
            'go': fetch_go_version,
            'nodejs': fetch_nodejs_version,
            'php': fetch_php_version,
            'redis': fetch_redis_version,
            'mongodb': fetch_mongodb_version,
            'mysql': fetch_mysql_version,
            'postgresql': fetch_postgresql_version,
            'docker': fetch_docker_version,
            'kubernetes': fetch_kubernetes_version
        }

        # 获取指定运行时版本
        if runtime_type:
            runtime_type = runtime_type.lower()
            if runtime_type in runtime_types:
                ver_data = runtime_types[runtime_type]()
                output.append(f"{runtime_type.upper()} 版本: {ver_data}")
            else:
                output.append(f"不支持的运行时类型: {runtime_type}")
                output.append(f"支持的运行时类型: {', '.join(runtime_types.keys())}")
        else:
            # 获取所有支持的运行时版本
            detected_runtimes = []
            for rt_type, get_version_func in runtime_types.items():
                try:
                    ver = get_version_func()
                    if ver and ver != '未检测到':
                        detected_runtimes.append(f"{rt_type.upper()}: {ver}")
                except Exception as e:
                    logger.debug(f"检测 {rt_type} 版本失败: {e}")

            if detected_runtimes:
                output.append("已检测到的运行时版本:")
                for info in detected_runtimes:
                    output.append(f"  - {info}")
            else:
                output.append("未检测到任何支持的运行时")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取运行时版本信息失败: {e}')
        return f'获取运行时版本信息失败: {e}'
def fetch_python_version():
    """
    获取Python版本
    """
    try:
        return platform.python_version()
    except Exception:
        return '未检测到'
def fetch_java_version():
    """
    获取Java版本
    """
    try:
        output = subprocess.run(['java', '-ver'], capture_output=True, text=True)
        if output.returncode == 0:
            for line in output.stderr.split('\n'):
                if 'ver' in line:
                    return line.strip().split()[2].strip('"')
        return '未检测到'
    except Exception:
        return '未检测到'
def fetch_go_version():
    """
    获取Go版本
    """
    try:
        output = subprocess.run(['go', 'ver'], capture_output=True, text=True)
        if output.returncode == 0:
            return output.stdout.strip().split()[-1]
        return '未检测到'
    except Exception:
        return '未检测到'
