import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_rsyslog')

def fetch_log_rsyslog():
    """
    采集rsyslog配置（日志服务配置/日志转发/存储路径/日志级别/过滤规则）

    返回:
        格式化的rsyslog配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== rsyslog配置信息 ===')

        # 获取rsyslog配置
        rsyslog_config = fetch_rsyslog_config()

        if not rsyslog_config:
            output.append('未检测到rsyslog配置')
        else:
            for key, value in rsyslog_config.items():
                output.append(f"{key}: {value}")

        # 显示rsyslog配置文件
        config_files = fetch_rsyslog_config_files()
        if config_files:
            output.append('\nrsyslog配置文件:')
            for file in config_files:
                output.append(f"  - {file}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取rsyslog配置失败: {e}')
        return f'获取rsyslog配置失败: {e}'

def fetch_rsyslog_config():
    """
    获取rsyslog配置
    """
    settings = {}

    try:
        # 检查rsyslog是否安装
        output = subprocess.run(['which', 'rsyslogd'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            settings['rsyslog状态'] = '已安装'
        else:
            settings['rsyslog状态'] = '未安装'

        # 检查rsyslog服务状态
        output = subprocess.run(['systemctl', 'status', 'rsyslog'], capture_output=True, text=True, timeout=10)

        if output.returncode == 0:
            if 'active (running)' in output.stdout:
                settings['服务状态'] = '运行中'
            else:
                settings['服务状态'] = '已安装但未运行'
        else:
            settings['服务状态'] = '未检测到服务'

        # 检查主要配置文件
        main_config = '/etc/rsyslog.conf'
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

                # 提取过滤规则
                filters = re.findall(r'\s*if\s+\$([^\s]+)\s+([^\n]+)', body)  # NOSONAR
                if filters:
                    settings['过滤规则数量'] = len(filters)

                # 提取转发配置
                forwards = re.findall(r'\s*\*\.\*\s+@([^\s]+)', body)  # NOSONAR
                if forwards:
                    settings['日志转发'] = ', '.join(forwards)

        # 检查配置目录
        config_dir = '/etc/rsyslog.d'
        if os.path.isdir(config_dir):
            config_files = os.listdir(config_dir)
            if config_files:
                settings['额外配置文件数量'] = len(config_files)

    except Exception as e:
        logger.error(f'获取rsyslog配置失败: {e}')
        raise  # 重新抛出异常，让上层函数捕获

    return settings

def fetch_rsyslog_config_files():
    """
    获取rsyslog配置文件
    """
    files = []

    try:
        # 主配置文件
        main_config = '/etc/rsyslog.conf'
        if os.path.exists(main_config):
            files.append(main_config)

        # 配置目录
        config_dir = '/etc/rsyslog.d'
        if os.path.isdir(config_dir):
            for file in os.listdir(config_dir):
                if file.endswith('.conf'):
                    files.append(os.path.join(config_dir, file))

    except Exception:
        pass

    return files

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_rsyslog",
    "function": fetch_log_rsyslog,
    "description": "采集rsyslog配置（日志服务配置/日志转发/存储路径/日志级别/过滤规则）",
    "parameters": {
        "type": "object",
        "properties": {}
    },
    "required": []
}
