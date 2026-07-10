from datetime import datetime
from typing import Dict, Any, List
import json
import logging
import os
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('oom_system_analysis')


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
def oom_system_analysis() -> Dict[str, Any]:
    """
    OOM分析-系统级OOM分析

    分析系统级别的OOM事件，包括：
    - OOM Killer触发历史分析
    - 被杀进程分析
    - 内存压力分析
    - 系统级OOM原因诊断

    返回:
        包含系统级OOM分析结果的字典
    """
    output = {
        'status': 'success',
        'analysis_time': datetime.now().isoformat(),
        'oom_events': [],
        'memory_pressure': {},
        'analysis_summary': {},
        'recommendations': [],
        'message': ''
    }

    try:
        # 分析OOM事件历史
        output['oom_events'] = examine_oom_events()

        # 分析内存压力
        output['memory_pressure'] = examine_memory_pressure()

        # 生成分析总结
        output['analysis_summary'] = produce_analysis_summary(
            output['oom_events'],
            output['memory_pressure']
        )

        # 生成建议
        output['recommendations'] = produce_recommendations(
            output['oom_events'],
            output['memory_pressure']
        )

        if output['oom_events']:
            output['message'] = f'发现 {len(output["oom_events"])} 个OOM事件'
        else:
            output['message'] = '未发现OOM事件'

        logger.info(output['message'])

    except Exception as e:
        output['status'] = 'error'
        output['message'] = f'分析失败: {e}'
        logger.error(output['message'])

    return output
def examine_oom_events() -> List[Dict[str, Any]]:
    """分析OOM事件历史"""
    events = []

    try:
        # 从dmesg获取OOM Killer日志
        dmesg_result = execute_command(['dmesg'])
        if dmesg_result['success']:
            body = dmesg_result['stdout']

            # 解析OOM Killer日志
            # 匹配模式: "Out of memory: Kill process ..."
            oom_pattern = r'Out of memory: Kill process (\d+) \(([^)]+)\)'
            for match in re.finditer(oom_pattern, body, re.IGNORECASE):
                events.append({
                    'pid': match.group(1),
                    'process_name': match.group(2),
                    'source': 'dmesg',
                    'timestamp': derive_timestamp(body, match.start()),
                    'type': 'oom_kill'
                })

            # 解析内存不足日志
            mem_pattern = r'invoked oom-killer: gfp_mask=0x([0-9a-f]+)'
            for match in re.finditer(mem_pattern, body, re.IGNORECASE):
                # 找到对应的进程信息
                context_start = max(0, match.start() - 500)
                context = body[context_start:match.end()]

                pid_match = re.search(r'([\w\-]+)\[(\d+)\]:', context)
                if pid_match:
                    events.append({
                        'pid': pid_match.group(2),
                        'process_name': pid_match.group(1),
                        'source': 'dmesg',
                        'timestamp': derive_timestamp(body, match.start()),
                        'type': 'oom_killer_invoked',
                        'gfp_mask': match.group(1)
                    })

        # 从/var/log/messages获取OOM日志（如果存在）
        if os.path.exists('/var/log/messages'):
            try:
                with open('/var/log/messages', 'r') as f:
                    body = f.read()

                oom_pattern = r'Out of memory: Kill process (\d+) \(([^)]+)\)'
                for match in re.finditer(oom_pattern, body, re.IGNORECASE):
                    events.append({
                        'pid': match.group(1),
                        'process_name': match.group(2),
                        'source': '/var/log/messages',
                        'timestamp': derive_syslog_timestamp(body, match.start()),
                        'type': 'oom_kill'
                    })
            except Exception:
                pass

        # 去重（基于pid和process_name）
        seen = set()
        unique_events = []
        for event in events:
            key = (event.get('pid'), event.get('process_name'))
            if key not in seen:
                seen.add(key)
                unique_events.append(event)

        events = unique_events

    except Exception as e:
        events.append({'error': str(e)})

    return events
def derive_timestamp(body: str, position: int) -> str:
    """从dmesg内容中提取时间戳"""
    try:
        # 查找最近的行首时间戳 [  123.456789]
        lines_before = body[:position].split('\n')
        for line in reversed(lines_before[-5:]):  # 检查前5行
            match = re.match(r'\[\s*([\d.]+)\]', line)
            if match:
                seconds = float(match.group(1))
                # 转换为可读格式
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    except Exception:
        pass
    return 'unknown'
def derive_syslog_timestamp(body: str, position: int) -> str:
    """从syslog内容中提取时间戳"""
    try:
        lines_before = body[:position].split('\n')
        if lines_before:
            last_line = lines_before[-1]
            # 匹配syslog格式: "Jun  1 12:34:56"
            match = re.match(r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', last_line)
            if match:
                return match.group(1)
    except Exception:
        pass
    return 'unknown'
def examine_memory_pressure() -> Dict[str, Any]:
    """分析内存压力情况"""
    pressure = {}

    try:
        # 检查内存压力接口（Linux 4.20+）
        if os.path.exists('/proc/pressure/memory'):
            with open('/proc/pressure/memory', 'r') as f:
                body = f.read()
                pressure['memory_pressure'] = body.strip()

                # 解析压力数据
                for line in body.split('\n'):
                    if line.startswith('some'):
                        pressure['some_avg10'] = derive_pressure_value(line, 'avg10')
                        pressure['some_avg60'] = derive_pressure_value(line, 'avg60')
                        pressure['some_avg300'] = derive_pressure_value(line, 'avg300')
                    elif line.startswith('full'):
                        pressure['full_avg10'] = derive_pressure_value(line, 'avg10')
                        pressure['full_avg60'] = derive_pressure_value(line, 'avg60')
                        pressure['full_avg300'] = derive_pressure_value(line, 'avg300')

        # 获取当前内存状态
        with open('/proc/meminfo', 'r') as f:
            body = f.read()

        mem_total = 0
        mem_available = 0

        for line in body.split('\n'):
            if line.startswith('MemTotal:'):
                mem_total = analyze_mem_value(line)
            elif line.startswith('MemAvailable:'):
                mem_available = analyze_mem_value(line)

        if mem_total > 0:
            usage_percent = (mem_total - mem_available) / mem_total * 100
            pressure['current_usage_percent'] = round(usage_percent, 2)
            pressure['current_status'] = 'critical' if usage_percent > 95 else 'warning' if usage_percent > 80 else 'normal'

        # 获取内存碎片信息
        if os.path.exists('/proc/buddyinfo'):
            with open('/proc/buddyinfo', 'r') as f:
                pressure['buddyinfo'] = f.read().strip()

        # 获取内存区域信息
        if os.path.exists('/proc/zoneinfo'):
            with open('/proc/zoneinfo', 'r') as f:
                zone_content = f.read()
                pressure['zoneinfo_summary'] = analyze_zoneinfo(zone_content)

    except Exception as e:
        pressure['error'] = str(e)

    return pressure
def derive_pressure_value(line: str, key: str) -> float:
    """从压力行中提取值"""
    try:
        pattern = rf'{key}=(\d+\.?\d*)'
        match = re.search(pattern, line)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return 0.0
def analyze_mem_value(line: str) -> int:
    """从meminfo行解析内存值"""
    try:
        parts = line.split()
        for i, part in enumerate(parts):
            if part.isdigit():
                return int(part)
    except Exception:
        pass
    return 0
