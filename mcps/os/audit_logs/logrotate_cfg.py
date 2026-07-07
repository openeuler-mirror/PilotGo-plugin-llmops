import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_logrotate')

def fetch_log_logrotate():
    """
    采集日志轮转配置（所有日志的轮转策略/保留份数/压缩/删除/执行时间）

    返回:
        格式化的日志轮转配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 日志轮转配置 ===')

        # 获取logrotate配置
        logrotate_config = fetch_logrotate_config()

        if not logrotate_config:
            output.append('未检测到logrotate配置')
        else:
            for key, value in logrotate_config.items():
                output.append(f"{key}: {value}")

        # 显示logrotate配置文件
        config_files = fetch_logrotate_config_files()
        if config_files:
            output.append('\nlogrotate配置文件:')
            for file in config_files:
                output.append(f"  - {file}")

        # 显示具体的轮转配置
        rotate_configs = fetch_rotate_configs()
        if rotate_configs:
            output.append('\n轮转配置详情:')
            for settings in rotate_configs:
                output.append(f"\n{settings}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取日志轮转配置失败: {e}')
        return f'获取日志轮转配置失败: {e}'

def fetch_logrotate_config():
    """
    获取logrotate配置
    """
    settings = {}

    try:
        # 检查logrotate是否安装
        output = subprocess.run(['which', 'logrotate'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            settings['logrotate状态'] = '已安装'
        else:
            settings['logrotate状态'] = '未安装'

        # 检查logrotate服务状态
        output = subprocess.run(['systemctl', 'status', 'logrotate.timer'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            if 'active (running)' in output.stdout:
                settings['服务状态'] = '运行中'
            else:
                settings['服务状态'] = '已安装但未运行'
        else:
            settings['服务状态'] = '未检测到服务'

        # 检查执行时间
        if os.path.exists('/etc/cron.daily/logrotate'):
            settings['执行时间'] = '每日（cron.daily）'
        elif os.path.exists('/etc/cron.weekly/logrotate'):
            settings['执行时间'] = '每周（cron.weekly）'
        elif os.path.exists('/etc/cron.monthly/logrotate'):
            settings['执行时间'] = '每月（cron.monthly）'

    except Exception as e:
        logger.error(f'获取logrotate配置失败: {e}')
        raise  # 重新抛出异常，让上层函数捕获

    return settings

def fetch_logrotate_config_files():
    """
    获取logrotate配置文件
    """
    files = []

    try:
        # 主配置文件
        main_config = '/etc/logrotate.conf'
        if os.path.exists(main_config):
            files.append(main_config)

        # 配置目录
        config_dir = '/etc/logrotate.d'
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                files.append(os.path.join(config_dir, file))

    except Exception:
        pass

    return files

def fetch_rotate_configs():
    """
    获取具体的轮转配置
    """
    configs = []

    try:
        # 检查主配置文件
        main_config = '/etc/logrotate.conf'
        if os.path.exists(main_config):
            with open(main_config, 'r', encoding='utf-8') as f:
                body = f.read()
                configs.append(f"主配置文件 ({main_config}):")
                configs.append(body)

        # 检查配置目录
        config_dir = '/etc/logrotate.d'
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                file_path = os.path.join(config_dir, file)
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        body = f.read()
                        configs.append(f"配置文件 ({file}):")
                        configs.append(body)

    except Exception as e:
        logger.error(f'获取轮转配置失败: {e}')
        raise  # 重新抛出异常，让上层函数捕获

    return configs

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_logrotate",
    "function": fetch_log_logrotate,
    "description": "采集日志轮转配置（所有日志的轮转策略/保留份数/压缩/删除/执行时间）",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}
