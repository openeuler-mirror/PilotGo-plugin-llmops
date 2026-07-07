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
