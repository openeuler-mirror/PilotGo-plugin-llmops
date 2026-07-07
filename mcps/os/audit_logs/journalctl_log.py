import logging
import os
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('log_journalctl')

def fetch_log_journalctl(since=None, until=None, unit=None, priority=None):
    """
    采集journald日志内容（按时间/服务/级别查询日志/最新日志/错误日志）

    参数:
        since: 起始时间，如 "1h ago", "2023-01-01"
        until: 结束时间，如 "now", "2023-01-02"
        unit: 服务名，如 "sshd", "nginx"
        priority: 日志级别，如 "err", "warn", "info"

    返回:
        格式化的journald日志内容字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== journald日志内容 ===')

        # 检查journalctl是否安装
        if not is_journalctl_installed():
            output.append('错误: journalctl命令未安装')
            output.append('=====================')
            return '\n'.join(output)

        # 构建journalctl命令
        cmd = ['journalctl']

        if since:
            cmd.extend(['--since', since])
        if until:
            cmd.extend(['--until', until])
        if unit:
            cmd.extend(['-u', unit])
        if priority:
            cmd.extend(['--priority', priority])

        # 添加其他选项
        cmd.extend(['--no-pager', '-n', '50'])  # 只显示50行

        # 执行命令
        cmd_result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
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

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取journald日志内容失败: {e}')
        return f'获取journald日志内容失败: {e}'

def is_journalctl_installed():
    """
    检查journalctl是否安装
    """
    try:
        output = subprocess.run(['which', 'journalctl'], capture_output=True, text=True)
        return output.returncode == 0
    except Exception:
        return False

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_log_journalctl",
    "function": fetch_log_journalctl,
    "description": "采集journald日志内容（按时间/服务/级别查询日志/最新日志/错误日志）",
    "parameters": {
        "type": "object",
        "properties": {
            "since": {
                "type": "string",
                "description": "起始时间，如 \"1h ago\", \"2023-01-01\""
            },
            "until": {
                "type": "string",
                "description": "结束时间，如 \"now\", \"2023-01-02\""
            },
            "unit": {
                "type": "string",
                "description": "服务名，如 \"sshd\", \"nginx\""
            },
            "priority": {
                "type": "string",
                "description": "日志级别，如 \"err\", \"warn\", \"info\""
            }
        },
        "required": []
    }
}
