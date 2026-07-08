from datetime import datetime
from typing import Dict, Any, List
import json
import json
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('oom_cgroup_analysis')


def execute_command(cmd: List[str], timeout: int = 30) -> Dict[str, Any]:
    """运行命令并返回结果"""
    try:
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            'success': output.returncode == 0,
            'stdout': output.stdout,
            'stderr': output.stderr,
            'returncode': output.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': '命令执行超时'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
def oom_cgroup_analysis() -> Dict[str, Any]:
    """
    OOM分析-cgroup OOM分析

    分析cgroup级别的OOM事件，包括：
    - cgroup内存限制配置
    - cgroup OOM事件历史
    - 容器/服务OOM分析
    - cgroup内存使用统计

    返回:
        包含cgroup OOM分析结果的字典
    """
    output = {
        'status': 'success',
        'analysis_time': datetime.now().isoformat(),
        'cgroup_version': spot_cgroup_version(),
        'cgroup_oom_events': [],
        'cgroup_memory_stats': [],
        'container_analysis': [],
        'analysis_summary': {},
        'recommendations': [],
        'message': ''
    }

    try:
        # 检测cgroup版本
        cgroup_version = spot_cgroup_version()
        output['cgroup_version'] = cgroup_version

        # 分析cgroup OOM事件
        output['cgroup_oom_events'] = examine_cgroup_oom_events()

        # 分析cgroup内存统计
        output['cgroup_memory_stats'] = examine_cgroup_memory_stats()

        # 分析容器OOM（如果存在容器）
        output['container_analysis'] = examine_container_oom()

        # 生成分析总结
        output['analysis_summary'] = produce_cgroup_summary(
            output['cgroup_oom_events'],
            output['cgroup_memory_stats']
        )

        # 生成建议
        output['recommendations'] = produce_cgroup_recommendations(
            output['cgroup_oom_events'],
            output['cgroup_memory_stats']
        )

        if output['cgroup_oom_events']:
            output['message'] = f'发现 {len(output["cgroup_oom_events"])} 个cgroup OOM事件'
        else:
            output['message'] = '未发现cgroup OOM事件'

        logger.info(output['message'])

    except Exception as e:
        output['status'] = 'error'
        output['message'] = f'分析失败: {e}'
        logger.error(output['message'])

    return output
def spot_cgroup_version() -> str:
    """检测cgroup版本"""
    try:
        # 检查cgroup2文件系统
        if os.path.exists('/sys/fs/cgroup/cgroup.controllers'):
            return 'cgroup2'

        # 检查cgroup v1
        if os.path.exists('/sys/fs/cgroup/memory'):
            return 'cgroup1'

        # 检查混合模式
        output = execute_command(['stat', '-fc', '%T', '/sys/fs/cgroup/'])
        if output['success'] and 'cgroup2fs' in output['stdout']:
            return 'cgroup2'
        elif output['success'] and 'tmpfs' in output['stdout']:
            return 'cgroup1'

    except Exception as e:
        logger.error(f'检测cgroup版本失败: {e}')

    return 'unknown'
def examine_cgroup_oom_events() -> List[Dict[str, Any]]:
    """分析cgroup OOM事件"""
    events = []

    try:
        # 从journalctl获取cgroup OOM日志
        journal_result = execute_command([
            'journalctl', '--since', '24 hours ago',
            '--grep', 'Memory cgroup|memory cgroup|oom', '-q', '--no-pager'
        ])

        if journal_result['success']:
            for line in journal_result['stdout'].split('\n'):
                if 'Memory cgroup' in line or 'memory cgroup' in line.lower():
                    event = analyze_cgroup_oom_log(line)
                    if event:
                        events.append(event)

        # 从dmesg获取cgroup OOM日志
        dmesg_result = execute_command(['dmesg'])
        if dmesg_result['success']:
            body = dmesg_result['stdout']

            # 匹配cgroup OOM模式
            cgroup_oom_pattern = r'Memory cgroup out of memory:.*Killed process (\d+) \(([^)]+)\)'
            for match in re.finditer(cgroup_oom_pattern, body, re.IGNORECASE):
                events.append({
                    'pid': match.group(1),
                    'process_name': match.group(2),
                    'source': 'dmesg',
                    'type': 'cgroup_oom_kill',
                    'timestamp': derive_dmesg_timestamp(body, match.start()),
                    'cgroup': derive_cgroup_from_context(body, match.start())
                })

        # 检查cgroup事件文件（cgroup v2）
        events.extend(verify_cgroup_v2_events())

        # 去重
        seen = set()
        unique_events = []
        for event in events:
            key = (event.get('pid'), event.get('process_name'), event.get('cgroup'))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)

        events = unique_events

    except Exception as e:
        events.append({'error': str(e)})

    return events
def analyze_cgroup_oom_log(line: str) -> Dict[str, Any]:
    """解析cgroup OOM日志行"""
    try:
        event = {'source': 'journalctl', 'raw': line}

        # 提取时间戳
        timestamp_match = re.match(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            event['timestamp'] = timestamp_match.group(1)

        # 提取cgroup路径
        cgroup_match = re.search(r'cgroup[:\s]+([^\s,]+)', line, re.IGNORECASE)
        if cgroup_match:
            event['cgroup'] = cgroup_match.group(1)

        # 提取进程信息
        pid_match = re.search(r'pid\s*(\d+)', line, re.IGNORECASE)
        if pid_match:
            event['pid'] = pid_match.group(1)

        # 提取进程名
        proc_match = re.search(r'process\s+([^\s,]+)', line, re.IGNORECASE)
        if proc_match:
            event['process_name'] = proc_match.group(1)

        if 'cgroup' in event or 'pid' in event:
            return event

    except Exception as e:
        return {'error': str(e), 'raw': line}

    return None
def derive_dmesg_timestamp(body: str, position: int) -> str:
    """从dmesg内容提取时间戳"""
    try:
        lines_before = body[:position].split('\n')
        for line in reversed(lines_before[-5:]):
            match = re.match(r'\[\s*([\d.]+)\]', line)
            if match:
                seconds = float(match.group(1))
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    except Exception:
        pass
    return 'unknown'
def derive_cgroup_from_context(body: str, position: int) -> str:
    """从上下文提取cgroup路径"""
    try:
        context_start = max(0, position - 1000)
        context = body[context_start:position]

        # 查找cgroup路径
        cgroup_match = re.search(r'cgroup[:\s]+(/[^\s,]+)', context, re.IGNORECASE)
        if cgroup_match:
            return cgroup_match.group(1)
    except Exception:
        pass
    return 'unknown'
