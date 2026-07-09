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
