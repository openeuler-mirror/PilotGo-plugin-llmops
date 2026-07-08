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
