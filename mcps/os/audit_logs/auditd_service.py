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
def fetch_auditd_config():
    """
    获取auditd配置
    """
    settings = {}

    try:
        # 检查auditd是否安装
        output = subprocess.run(
            ['which', 'auditd'],
            capture_output=True,
            text=True,
            timeout=10  # 添加超时防止长时间等待
        )

        if output.returncode == 0:
            settings['auditd状态'] = '已安装'
        else:
            settings['auditd状态'] = '未安装'

        # 检查auditd服务状态
        output = subprocess.run(
            ['systemctl', 'status', 'auditd'],
            capture_output=True,
            text=True,
            timeout=10  # 添加超时防止长时间等待
        )

        if output.returncode == 0:
            if 'active (running)' in output.stdout:
                settings['服务状态'] = '运行中'
            else:
                settings['服务状态'] = '已安装但未运行'
        else:
            settings['服务状态'] = '未检测到服务'

        # 检查主要配置文件
        main_config = '/etc/audit/auditd.conf'
        if os.path.exists(main_config):
            with open(main_config, 'r', encoding='utf-8') as f:
                body = f.read()

                # 提取配置项
                config_items = re.findall(r'\s*(\w+)\s*=\s*([^\n#]+)', body)  # NOSONAR
                for key, value in config_items:
                    if key not in ['log_file', 'log_group', 'priority_boost', 'flush', 'freq', 'max_log_file', 'num_logs', 'disp_qos', 'dispatcher', 'name_format', 'node_name', 'space_left', 'space_left_action', 'action_mail_acct', 'admin_space_left', 'admin_space_left_action', 'disk_full_action', 'disk_error_action', 'tcp_client_ports', 'tcp_server_ports', 'enable_krb5', 'krb5_principal', 'krb5_key_file', 'q_depth', 'overflow_action', 'max_restarts', 'daemon_euid', 'daemon_emask']:
                        if key.lower() in ['arch', 'max_log_file', 'num_logs', 'space_left', 'admin_space_left', 'space_left_action', 'admin_space_left_action', 'disk_full_action', 'disk_error_action', 'flush']:
                            settings[key] = value.strip()

        # 检查日志存储路径
        log_dir = '/var/log/audit'
        if os.path.isdir(log_dir):
            settings['日志存储路径'] = log_dir

            # 检查日志文件数量
            try:
                log_files = os.listdir(log_dir)
                settings['日志文件数量'] = len(log_files)
            except PermissionError:
                settings['日志文件数量'] = '访问被拒绝'

    except subprocess.TimeoutExpired as e:
        logger.error(f'获取auditd配置超时: {e}')
        raise  # 重新抛出异常以便上层捕获
    except Exception as e:
        logger.error(f'获取auditd配置失败: {e}')
        raise  # 重新抛出异常以便上层捕获

    return settings
def fetch_auditd_config_files():
    """
    获取auditd配置文件
    """
    files = []

    try:
        # 主配置文件
        main_config = '/etc/audit/auditd.conf'
        if os.path.exists(main_config):
            files.append(main_config)

        # 规则文件
        rule_files = [
            '/etc/audit/rules.d/',
            '/etc/audit/audit.rules'
        ]

        for file in rule_files:
            if os.path.exists(file):
                files.append(file)

    except Exception:
        pass

    return files
