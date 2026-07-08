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
logger = logging.getLogger('oom_basic_info')


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
def oom_basic_info() -> Dict[str, Any]:
    """
    OOM分析-基础信息收集

    收集系统OOM相关的基础信息，包括：
    - 系统内存信息
    - OOM Killer配置
    - 最近的OOM日志
    - 进程内存使用统计

    返回:
        包含OOM基础信息的字典
    """
    output = {
        'status': 'success',
        'collect_time': datetime.now().isoformat(),
        'memory_info': {},
        'oom_config': {},
        'oom_logs': [],
        'top_memory_processes': [],
        'message': ''
    }

    try:
        # 收集内存信息
        output['memory_info'] = gather_memory_info()

        # 收集OOM Killer配置
        output['oom_config'] = gather_oom_config()

        # 收集OOM日志
        output['oom_logs'] = gather_oom_logs()

        # 收集内存使用最多的进程
        output['top_memory_processes'] = gather_top_memory_processes()

        output['message'] = 'OOM基础信息收集完成'
        logger.info(output['message'])

    except Exception as e:
        output['status'] = 'error'
        output['message'] = f'信息收集失败: {e}'
        logger.error(output['message'])

    return output
def gather_memory_info() -> Dict[str, Any]:
    """收集系统内存信息"""
    mem_data = {}

    try:
        # 从/proc/meminfo读取内存信息
        with open('/proc/meminfo', 'r') as f:
            body = f.read()

        for line in body.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                mem_data[key.strip()] = value.strip()

        # 计算内存使用率
        if 'MemTotal' in mem_data and 'MemAvailable' in mem_data:
            total = analyze_mem_value(mem_data['MemTotal'])
            available = analyze_mem_value(mem_data['MemAvailable'])
            if total > 0:
                mem_data['usage_percent'] = round((total - available) / total * 100, 2)

        # 获取Swap信息
        swap_result = execute_command(['swapon', '--show=NAME,SIZE,USED,TYPE', '--noheadings'])
        if swap_result['success']:
            mem_data['swap_info'] = swap_result['stdout'].strip()

        # 获取内存统计
        stat_result = execute_command(['vmstat', '-s'])
        if stat_result['success']:
            mem_data['vmstat'] = stat_result['stdout'].strip()

    except Exception as e:
        mem_data['error'] = str(e)

    return mem_data
def analyze_mem_value(value_str: str) -> int:
    """解析内存值（如 '16384000 kB' -> 16384000）"""
    try:
        parts = value_str.strip().split()
        if len(parts) >= 1:
            return int(parts[0])
    except Exception:
        pass
    return 0
def gather_oom_config() -> Dict[str, Any]:
    """收集OOM Killer配置"""
    settings = {}

    try:
        # OOM Killer开关
        if os.path.exists('/proc/sys/vm/oom_kill_allocating_task'):
            with open('/proc/sys/vm/oom_kill_allocating_task', 'r') as f:
                settings['oom_kill_allocating_task'] = f.read().strip()

        # OOM Killer panic开关
        if os.path.exists('/proc/sys/vm/panic_on_oom'):
            with open('/proc/sys/vm/panic_on_oom', 'r') as f:
                settings['panic_on_oom'] = f.read().strip()

        # 内存过量使用配置
        if os.path.exists('/proc/sys/vm/overcommit_memory'):
            with open('/proc/sys/vm/overcommit_memory', 'r') as f:
                settings['overcommit_memory'] = f.read().strip()

        # 过量使用比例
        if os.path.exists('/proc/sys/vm/overcommit_ratio'):
            with open('/proc/sys/vm/overcommit_ratio', 'r') as f:
                settings['overcommit_ratio'] = f.read().strip()

        # 解释配置含义
        settings['explanations'] = {
            'oom_kill_allocating_task': '1=直接kill分配内存的进程, 0=选择得分最高的进程',
            'panic_on_oom': '0=触发OOM Killer, 1=触发panic, 2=强制panic（无论是否配置mempolicy/cpuset）',
            'overcommit_memory': '0=启发式过量使用, 1=总是允许过量使用, 2=不允许过量使用',
            'overcommit_ratio': '可过量使用的内存百分比（当overcommit_memory=2时有效）'
        }

    except Exception as e:
        settings['error'] = str(e)

    return settings
def gather_oom_logs() -> List[Dict[str, Any]]:
    """收集OOM相关的日志"""
    oom_logs = []

    try:
        # 从dmesg获取OOM日志
        dmesg_result = execute_command(['dmesg', '--level=err,warn'])
        if dmesg_result['success']:
            for line in dmesg_result['stdout'].split('\n'):
                if 'oom' in line.lower() or 'out of memory' in line.lower():
                    oom_logs.append({
                        'source': 'dmesg',
                        'message': line.strip()
                    })

        # 从journalctl获取OOM日志
        journal_result = execute_command([
            'journalctl', '-k', '--since', '24 hours ago',
            '--grep', 'oom|Out of memory', '-q', '--no-pager'
        ])
        if journal_result['success']:
            for line in journal_result['stdout'].split('\n'):
                if line.strip():
                    oom_logs.append({
                        'source': 'journalctl',
                        'message': line.strip()
                    })

        # 去重
        seen = set()
        unique_logs = []
        for log in oom_logs:
            msg = log['message']
            if msg not in seen:
                seen.add(msg)
                unique_logs.append(log)

        oom_logs = unique_logs[:20]  # 限制数量

    except Exception as e:
        oom_logs.append({'source': 'error', 'message': str(e)})

    return oom_logs
def gather_top_memory_processes() -> List[Dict[str, Any]]:
    """收集内存使用最多的进程"""
    processes = []

    try:
        # 使用ps获取内存使用最多的进程
        ps_result = execute_command([
            'ps', 'aux', '--sort=-%mem',
            '--no-headers'
        ])

        if ps_result['success']:
            lines = ps_result['stdout'].strip().split('\n')
            for line in lines[:10]:  # 取前10个
                parts = line.split()
                if len(parts) >= 11:
                    processes.append({
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu_percent': parts[2],
                        'mem_percent': parts[3],
                        'vsz': parts[4],
                        'rss': parts[5],
                        'command': ' '.join(parts[10:])
                    })

        # 获取进程oom_score
        for proc in processes:
            try:
                pid = proc['pid']
                oom_score_path = f'/proc/{pid}/oom_score'
                if os.path.exists(oom_score_path):
                    with open(oom_score_path, 'r') as f:
                        proc['oom_score'] = f.read().strip()

                oom_adj_path = f'/proc/{pid}/oom_score_adj'
                if os.path.exists(oom_adj_path):
                    with open(oom_adj_path, 'r') as f:
                        proc['oom_score_adj'] = f.read().strip()
            except Exception:
                pass

    except Exception as e:
        processes.append({'error': str(e)})

    return processes


if __name__ == '__main__':
    # 测试
    output = oom_basic_info()
    print(json.dumps(output, indent=2, ensure_ascii=False))
