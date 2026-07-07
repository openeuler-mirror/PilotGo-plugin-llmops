import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_journald')

def fetch_log_journald():
    """
    采集journald配置（systemd日志/存储路径/日志大小/保留策略/转发配置）

    返回:
        格式化的journald配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== journald配置信息 ===')

        # 获取journald配置
        journald_config = fetch_journald_config()

        if not journald_config:
            output.append('未检测到journald配置')
        else:
            for key, value in journald_config.items():
                output.append(f"{key}: {value}")

        # 显示journald配置文件
        config_files = fetch_journald_config_files()
        if config_files:
            output.append('\njournald配置文件:')
            for file in config_files:
                output.append(f"  - {file}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取journald配置失败: {e}')
        return f'获取journald配置失败: {e}'

def fetch_journald_config():
    """
    获取journald配置
    """
    settings = {}

    try:
        # 检查journald是否安装
        output = subprocess.run(['which', 'systemd-journald'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            settings['journald状态'] = '已安装'
        else:
            settings['journald状态'] = '未安装'

        # 检查journald服务状态
        output = subprocess.run(['systemctl', 'status', 'systemd-journald'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            if 'active (running)' in output.stdout:
                settings['服务状态'] = '运行中'
            else:
                settings['服务状态'] = '已安装但未运行'
        else:
            settings['服务状态'] = '未检测到服务'

        # 检查主要配置文件
        main_config = '/etc/systemd/journald.conf'
        if os.path.exists(main_config):
            with open(main_config, 'r', encoding='utf-8') as f:
                body = f.read()

                # 提取配置项
                config_items = re.findall(r'\s*(\w+)\s*=\s*([^\n]+)', body)  # NOSONAR
                for key, value in config_items:
                    if key not in ['#']:
                        settings[key] = value

        # 检查日志存储路径
        log_paths = [
            '/var/log/journal',
            '/run/log/journal'
        ]
        existing_paths = [path for path in log_paths if os.path.isdir(path)]

        if existing_paths:
            settings['日志存储路径'] = ', '.join(existing_paths)

        # 检查日志大小
        output = subprocess.run(['journalctl', '--disk-usage'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            settings['日志磁盘使用'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取journald配置失败: {e}')
        raise  # 重新抛出异常，让上层函数捕获

    return settings

def fetch_journald_config_files():
    """
    获取journald配置文件
    """
    files = []

    try:
        # 主配置文件
        main_config = '/etc/systemd/journald.conf'
        if os.path.exists(main_config):
            files.append(main_config)

        # 配置目录
        config_dir = '/etc/systemd/journald.conf.d'
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.conf'):
                    files.append(os.path.join(config_dir, file))

    except Exception:
        pass

    return files

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_journald",
    "function": fetch_log_journald,
    "description": "采集journald配置（systemd日志/存储路径/日志大小/保留策略/转发配置）",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}
