from datetime import datetime
from datetime import datetime
from datetime import datetime
from datetime import datetime
from datetime import datetime
from datetime import datetime
import logging
import os
import re
import subprocess

from .rd_shared import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('redis_base_path')

def fetch_redis_base_path(path_type=None):
    """
    采集Redis安装路径、配置文件路径、持久化文件路径（RDB/AOF）、日志文件路径

    参数:
        path_type: 指定要采集的路径类型，可选值：
                   - "install": 仅采集安装路径
                   - "config": 仅采集配置文件路径
                   - "persistence": 仅采集持久化文件路径（RDB/AOF）
                   - "log": 仅采集日志文件路径
                   - "all": 采集所有路径信息（默认）

    返回:
        格式化的Redis路径信息字符串
    """
    try:
        output = []
        output.append('=== Redis路径信息 ===')

        redis_pid = find_redis_pid()

        if not redis_pid:
            output.append('未检测到运行中的Redis进程')
            output.append('尝试通过配置文件查找路径信息...')

            config_paths = locate_redis_config_paths()
            if config_paths:
                output.append('\n找到的配置文件:')
                for cfg_filepath in config_paths:
                    output.append(f"  {cfg_filepath}")

                    cfg_state = analyze_redis_config(cfg_filepath)
                    if cfg_state:
                        for key, val in cfg_state.items():
                            output.append(f"    {key}: {val}")
            else:
                output.append('未找到Redis配置文件')

            output.append('=====================')
            return '\n'.join(output)

        output.append(f'检测到Redis进程: PID {redis_pid}')

        if path_type is None or path_type == "all" or path_type == "install":
            install_info = fetch_redis_install_path(redis_pid)
            if install_info:
                output.append('\n安装路径:')
                for key, val in install_info.items():
                    output.append(f"  {key}: {val}")

        if path_type is None or path_type == "all" or path_type == "config":
            cfg_state = fetch_redis_config_path(redis_pid)
            if cfg_state:
                output.append('\n配置文件路径:')
                for key, val in cfg_state.items():
                    output.append(f"  {key}: {val}")

        if path_type is None or path_type == "all" or path_type == "persistence":
            persistence_info = fetch_redis_persistence_path(redis_pid)
            if persistence_info:
                output.append('\n持久化文件路径:')
                for key, val in persistence_info.items():
                    output.append(f"  {key}: {val}")

        if path_type is None or path_type == "all" or path_type == "log":
            log_info = fetch_redis_log_path(redis_pid)
            if log_info:
                output.append('\n日志文件路径:')
                for key, val in log_info.items():
                    output.append(f"  {key}: {val}")

        output.append('\n采样时间:')
        output.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Redis路径信息失败: {str(e)}')
        return f'获取Redis路径信息失败: {str(e)}'
