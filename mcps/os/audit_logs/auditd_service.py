import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_auditd')

def fetch_log_auditd():
    """
    采集auditd审计配置（审计服务/规则/日志存储/保留策略/审计级别）

    返回:
        格式化的auditd审计配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== auditd配置信息 ===')

        # 获取auditd配置
        auditd_config = fetch_auditd_config()

        if not auditd_config:
            output.append('未检测到auditd配置')
        else:
            for key, value in auditd_config.items():
                output.append(f"{key}: {value}")

        # 显示auditd配置文件
        config_files = fetch_auditd_config_files()
        if config_files:
            output.append('\nauditd配置文件:')
            for file in config_files:
                output.append(f"  - {file}")

        # 显示审计规则
        audit_rules = fetch_audit_rules()
        if audit_rules:
            output.append('\n审计规则:')
            for rule in audit_rules:
                output.append(f"  - {rule}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取auditd配置失败: {e}')
        return f'获取auditd配置失败: {e}'
