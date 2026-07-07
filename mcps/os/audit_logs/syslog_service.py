import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_syslog')

def fetch_log_syslog():
    """
    采集传统syslog配置（旧版syslog服务/日志级别/存储路径/设备日志配置）

    返回:
        格式化的syslog配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 传统syslog配置信息 ===')

        # 获取syslog配置
        syslog_config = fetch_syslog_config()

        if not syslog_config:
            output.append('未检测到传统syslog配置')
        else:
            for key, value in syslog_config.items():
                output.append(f"{key}: {value}")

        # 显示syslog配置文件
        config_files = fetch_syslog_config_files()
        if config_files:
            output.append('\nsyslog配置文件:')
            for file in config_files:
                output.append(f"  - {file}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取传统syslog配置失败: {e}')
        return f'获取传统syslog配置失败: {e}'

def fetch_syslog_config():
    """
    获取syslog配置
    """
    settings = {}

    try:
        # 检查syslog是否安装
        output = subprocess.run(['which', 'syslogd'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            settings['syslog状态'] = '已安装'
        else:
            settings['syslog状态'] = '未安装'

        # 检查syslog服务状态
        output = subprocess.run(['systemctl', 'status', 'syslog'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            if 'active (running)' in output.stdout:
                settings['服务状态'] = '运行中'
            else:
                settings['服务状态'] = '已安装但未运行'
        else:
            settings['服务状态'] = '未检测到服务'

        # 检查主要配置文件
        main_config = '/etc/syslog.conf'
        if os.path.exists(main_config):
            with open(main_config, 'r', encoding='utf-8') as f:
                body = f.read()

                # 提取日志存储路径
                log_paths = re.findall(r'\s*\*\.\*\s+(/[^\s]+)', body)  # NOSONAR
                if log_paths:
                    settings['日志存储路径'] = ', '.join(log_paths)

                # 提取日志级别
                log_levels = re.findall(r'\s*(\w+\.\w+)\s+', body)  # NOSONAR
                if log_levels:
                    settings['日志级别'] = ', '.join(set(log_levels))

                # 提取设备日志配置
                device_configs = re.findall(r'\s*(kern\.\w+)\s+([^\n]+)', body)  # NOSONAR
                if device_configs:
                    settings['设备日志配置'] = '已配置'

        # 检查替代配置文件
        alt_config = '/etc/rsyslog.conf'
        if os.path.exists(alt_config) and not os.path.exists(main_config):
            with open(alt_config, 'r', encoding='utf-8') as f:
                body = f.read()
                if 'syslog' in body.lower():
                    settings['使用rsyslog作为syslog替代品'] = '是'

    except Exception as e:
        logger.error(f'获取syslog配置失败: {e}')
        raise  # 重新抛出异常，让上级函数处理

    return settings

def fetch_syslog_config_files():
    """
    获取syslog配置文件
    """
    files = []

    try:
        # 主配置文件
        main_config = '/etc/syslog.conf'
        if os.path.exists(main_config):
            files.append(main_config)

        # 替代配置文件
        alt_config = '/etc/rsyslog.conf'
        if os.path.exists(alt_config):
            files.append(alt_config)

        # 配置目录
        config_dir = '/etc/syslog.d'
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.conf'):
                    files.append(os.path.join(config_dir, file))

    except Exception:
        pass

    return files

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_syslog",
    "function": fetch_log_syslog,
    "description": "采集传统syslog配置（旧版syslog服务/日志级别/存储路径/设备日志配置）",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}
