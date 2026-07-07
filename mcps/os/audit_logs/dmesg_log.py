from datetime import datetime, timedelta
import logging
import os
import re
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_dmesg')

def fetch_log_dmesg(level=None, last=None):
    """
    采集内核日志（dmesg/内核启动/硬件检测/驱动加载/错误信息/按级别过滤）

    参数:
        level: 日志级别，如 "err", "warn", "info"
        last: 显示最近的行数，如 "100"

    返回:
        格式化的内核日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 内核日志内容 ===')

        # 安全校验：验证 level 参数（如果提供）
        if level:
            is_valid, error_msg = validate_identifier_param(level)
            if not is_valid:
                logger.error(f'日志级别不合法：{error_msg}')
                output.append(f'错误：日志级别不合法 - {error_msg}')
                output.append('=====================')
                return '\n'.join(output)

        # 安全校验：验证 last 参数（如果提供）
        if last:
            try:
                last_int = int(last)
                if last_int <= 0 or last_int > 10000:
                    logger.error(f'行数参数超出范围：{last}')
                    output.append(f'错误：行数参数必须在 1-10000 之间')
                    output.append('=====================')
                    return '\n'.join(output)
            except ValueError:
                logger.error(f'无效的行数参数：{last}')
                output.append(f'错误：无效的行数参数 {last}')
                output.append('=====================')
                return '\n'.join(output)

        # 检查 dmesg 是否可用
        if not is_dmesg_available():
            output.append('错误: dmesg命令不可用')
            output.append('=====================')
            return '\n'.join(output)

        # 构建 dmesg 命令
        cmd = ['dmesg']

        if level:
            # 映射日志级别
            level_map = {
                'err': 'err',
                'error': 'err',
                'warn': 'warn',
                'warning': 'warn',
                'info': 'info',
                'debug': 'debug'
            }

            if level in level_map:
                cmd.extend(['--level', level_map[level]])

        if last:
            try:
                lines = int(last)
                cmd.extend(['--lines', str(lines)])
            except ValueError:
                output.append(f'错误: 无效的行数参数 {last}')

        # 执行命令
        cmd_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10  # 添加超时防止长时间等待
        )

        if cmd_result.returncode == 0:
            logs = cmd_result.stdout.strip()
            if logs:
                output.append('\n日志内容:')
                output.append(logs)
            else:
                output.append('未检测到日志内容')
        else:
            output.append(f'执行命令失败: {cmd_result.stderr.strip()}')

        # 显示命令信息
        output.append('\n执行命令:')
        output.append(' '.join(cmd))

        # 显示内核版本
        kernel_version = fetch_kernel_version()
        if kernel_version:
            output.append(f'\n内核版本: {kernel_version}')

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取内核日志内容失败: {e}')
        return f'获取内核日志内容失败: {e}'

def is_dmesg_available():
    """
    检查dmesg是否可用
    """
    try:
        output = subprocess.run(
            ['which', 'dmesg'],
            capture_output=True,
            text=True,
            timeout=5  # 添加超时
        )
        return output.returncode == 0
    except Exception:
        return False

def fetch_kernel_version():
    """
    获取内核版本
    """
    try:
        output = subprocess.run(
            ['uname', '-r'],
            capture_output=True,
            text=True,
            timeout=5  # 添加超时
        )
        if output.returncode == 0:
            return output.stdout.strip()
    except Exception:
        pass
    return None

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_dmesg",
    "function": fetch_log_dmesg,
    "description": "采集内核日志（dmesg/内核启动/硬件检测/驱动加载/错误信息/按级别过滤）",
    "parameters": {
        "type": "object",
        "properties": {
            "level": {
                "type": "string",
                "description": "日志级别，如 \"err\", \"warn\", \"info\""
            },
            "last": {
                "type": "string",
                "description": "显示最近的行数，如 \"100\""
            }
        },
        "required": []
    }
}
