#!/usr/bin/env python3
"""
Nginx日志切割规则设置工具
支持设置日志切割规则（按大小/时间）、保留天数、是否压缩、切割后通知
"""

import os
import re
import json
import logging
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_rotate')

RETENTION_DAYS = 7

def verify_nginx_installation() -> bool:
    """
    检查Nginx是否已安装
    
    返回:
        bool: Nginx是否已安装
    """
    try:
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False

def fetch_nginx_config_path() -> Optional[str]:
    """
    获取Nginx主配置文件路径
    
    返回:
        str: 主配置文件路径，如果找不到返回None
    """
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0:
            output = output.stdout if output.stdout else output.stderr
            config_match = re.search(r'nginx: the configuration file ([^\s]+)', output)  # NOSONAR
            if config_match:
                return config_match.group(1)
        
        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    except Exception as e:
        logger.error(f"获取Nginx配置路径失败: {e}")
        return None

def save_config_file(cfg_filepath: str) -> str:
    """
    备份配置文件
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        str: 备份文件路径
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{cfg_filepath}.backup.{timestamp}"
        shutil.copy2(cfg_filepath, backup_path)
        logger.info(f"配置文件已备份到: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"备份配置文件失败: {e}")
        raise

def analyze_nginx_config(cfg_filepath: str) -> Dict[str, Any]:
    """
    解析Nginx配置文件，获取日志文件路径
    
    参数:
        cfg_filepath: 配置文件路径
        
    返回:
        dict: 解析后的配置信息
    """
    settings = {
        'log_files': [],
        'error_logs': [],
        'access_logs': []
    }
    
    try:
        if not os.path.exists(cfg_filepath):
            return settings
        
        with open(cfg_filepath, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 移除注释
        body = re.sub(r'#.*$', '', body, flags=re.MULTILINE)  # NOSONAR
        
        # 解析错误日志路径
        error_log_pattern = r'error_log\s+([^;\s]+)'  # NOSONAR
        error_logs = re.findall(error_log_pattern, body)  # NOSONAR
        for log_path in error_logs:
            if log_path not in ['stderr', 'syslog']:
                settings['error_logs'].append(log_path.strip('"\''))
        
        # 解析访问日志路径
        access_log_pattern = r'access_log\s+([^;\s]+)'  # NOSONAR
        access_logs = re.findall(access_log_pattern, body)  # NOSONAR
        for log_path in access_logs:
            if log_path not in ['off']:
                settings['access_logs'].append(log_path.strip('"\''))
        
        # 合并所有日志文件
        settings['log_files'] = list(set(settings['error_logs'] + settings['access_logs']))
        
    except Exception as e:
        logger.error(f"解析Nginx配置文件失败: {e}")
    
    return settings

def build_logrotate_config(log_files: List[str], rotation_type: str, 
                          rotation_value: str, retention_days: int,
                          compress: bool, postrotate_script: str) -> str:
    """
    创建logrotate配置文件内容
    
    参数:
        log_files: 日志文件列表
        rotation_type: 切割类型 (size/time)
        rotation_value: 切割值 (如: 100M, daily, weekly)
        retention_days: 保留天数
        compress: 是否压缩
        postrotate_script: 切割后执行的脚本
        
    返回:
        str: logrotate配置内容
    """
    config_lines = []
    
    for log_file in log_files:
        config_lines.append(f'"{log_file}" {{')
        
        if rotation_type == 'size':
            config_lines.append(f'    size {rotation_value}')
        else:  # time-based rotation
            config_lines.append(f'    {rotation_value}')
        
        config_lines.append(f'    rotate {retention_days}')
        config_lines.append(f'    copytruncate')
        config_lines.append(f'    missingok')
        config_lines.append(f'    notifempty')
        config_lines.append(f'    create 644 nginx nginx')
        
        if compress:
            config_lines.append(f'    compress')
            config_lines.append(f'    delaycompress')
        
        if postrotate_script:
            config_lines.append(f'    postrotate')
            config_lines.append(f'        {postrotate_script}')
            config_lines.append(f'    endscript')
        
        config_lines.append('}')
        config_lines.append('')
    
    return '\n'.join(config_lines)

def setup_logrotate_config(config_content: str, config_name: str = 'nginx') -> bool:
    """
    安装logrotate配置文件
    
    参数:
        config_content: 配置内容
        config_name: 配置文件名
        
    返回:
        bool: 是否安装成功
    """
    try:
        logrotate_dir = '/etc/logrotate.d'
        if not os.path.exists(logrotate_dir):
            os.makedirs(logrotate_dir, exist_ok=True)
        
        cfg_filepath = os.path.join(logrotate_dir, config_name)
        
        # 备份现有配置
        if os.path.exists(cfg_filepath):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{cfg_filepath}.backup.{timestamp}"
            shutil.copy2(cfg_filepath, backup_path)
            logger.info(f"现有logrotate配置已备份到: {backup_path}")
        
        # 写入新配置
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # 设置权限
        os.chmod(cfg_filepath, 0o644)  # NOSONAR
        logger.info(f"logrotate配置已安装到: {cfg_filepath}")
        return True
        
    except Exception as e:
        logger.error(f"安装logrotate配置失败: {e}")
        return False

def build_custom_rotation_script(log_files: List[str], rotation_type: str,
                                 rotation_value: str, retention_days: int,
                                 compress: bool, notification_script: str) -> str:
    """
    创建自定义日志切割脚本
    
    参数:
        log_files: 日志文件列表
        rotation_type: 切割类型
        rotation_value: 切割值
        retention_days: 保留天数
        compress: 是否压缩
        notification_script: 通知脚本
        
    返回:
        str: 自定义脚本内容
    """
    script_content = f"""#!/bin/bash
# Nginx日志自定义切割脚本
# 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

LOG_FILES=({" ".join([f'"{f}"' for f in log_files])})
RETENTION_DAYS={retention_days}
COMPRESS={'true' if compress else 'false'}

# 日志函数
log_message() {{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> /var/log/nginx-rotation.log
}}

# 切割函数
rotate_logs() {{
    for LOG_FILE in ${{LOG_FILES[@]}}; do
        if [ ! -f "$LOG_FILE" ]; then
            log_message "警告: 日志文件 $LOG_FILE 不存在"
            continue
        fi
        
        # 创建时间戳备份
        TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
        BACKUP_FILE="$LOG_FILE.$TIMESTAMP"
        
        # 复制日志文件
        cp "$LOG_FILE" "$BACKUP_FILE"
        
        # 清空原日志文件
        > "$LOG_FILE"
        
        log_message "已切割日志文件: $LOG_FILE -> $BACKUP_FILE"
        
        # 压缩备份文件
        if [ "$COMPRESS" = "true" ]; then
            gzip "$BACKUP_FILE"
            log_message "已压缩备份文件: $BACKUP_FILE.gz"
        fi
    done
}}

# 清理旧文件
cleanup_old_files() {{
    for LOG_FILE in ${{LOG_FILES[@]}}; do
        if [ ! -f "$LOG_FILE" ]; then
            continue
        fi
        
        # 查找并删除超过保留天数的文件
        find $(dirname "$LOG_FILE") -name "$(basename "$LOG_FILE")*.gz" -mtime +$RETENTION_DAYS -delete
        find $(dirname "$LOG_FILE") -name "$(basename "$LOG_FILE")*" ! -name "$(basename "$LOG_FILE")" -mtime +$RETENTION_DAYS -delete
        
        log_message "已清理超过{RETENTION_DAYS}天的旧日志文件"
    done
}}

# 发送通知
send_notification() {{
    if [ -n "{notification_script}" ]; then
        {notification_script}
        log_message "已发送通知"
    fi
}}

# 主执行流程
main() {{
    log_message "开始执行Nginx日志切割"
    rotate_logs
    cleanup_old_files
    send_notification
    log_message "Nginx日志切割完成"
}}

main "$@"
"""
    return script_content

def setup_custom_script(script_content: str, script_name: str = 'nginx-log-rotate') -> str:
    """
    安装自定义切割脚本
    
    参数:
        script_content: 脚本内容
        script_name: 脚本名称
        
    返回:
        str: 脚本安装路径
    """
    try:
        script_dir = '/usr/local/bin'
        if not os.path.exists(script_dir):
            os.makedirs(script_dir, exist_ok=True)
        
        script_path = os.path.join(script_dir, script_name)
        
        # 写入脚本
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)  # NOSONAR
        logger.info(f"自定义切割脚本已安装到: {script_path}")
        return script_path
        
    except Exception as e:
        logger.error(f"安装自定义脚本失败: {e}")
        raise

def setup_cron_job(script_path: str, rotation_type: str, rotation_value: str) -> bool:
    """
    设置定时任务
    
    参数:
        script_path: 脚本路径
        rotation_type: 切割类型
        rotation_value: 切割值
        
    返回:
        bool: 是否设置成功
    """
    try:
        cron_content = ""
        
        if rotation_type == 'time':
            if rotation_value == 'daily':
                cron_content = f"0 0 * * * root {script_path}\n"
            elif rotation_value == 'weekly':
                cron_content = f"0 0 * * 0 root {script_path}\n"
            elif rotation_value == 'monthly':
                cron_content = f"0 0 1 * * root {script_path}\n"
            elif rotation_value == 'hourly':
                cron_content = f"0 * * * * root {script_path}\n"
        else:
            # 对于按大小切割，每小时检查一次
            cron_content = f"0 * * * * root {script_path}\n"
        
        if cron_content:
            cron_file = '/etc/cron.d/nginx-log-rotate'
            with open(cron_file, 'w', encoding='utf-8') as f:
                f.write(cron_content)
            
            os.chmod(cron_file, 0o644)  # NOSONAR
            logger.info(f"定时任务已设置: {cron_file}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"设置定时任务失败: {e}")
        return False