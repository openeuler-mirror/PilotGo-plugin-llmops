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
