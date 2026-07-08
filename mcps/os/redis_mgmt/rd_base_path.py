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
def locate_redis_config_paths():
    """
    查找Redis配置文件路径
    """
    config_paths = []

    try:
        common_paths = [
            '/etc/redis/redis.conf',
            '/etc/redis.conf',
            '/usr/local/etc/redis.conf',
            '/usr/local/redis/redis.conf',
            '/opt/redis/redis.conf',
            '/home/redis/redis.conf',
            '/var/lib/redis/redis.conf'
        ]

        for path in common_paths:
            if os.path.exists(path):
                config_paths.append(path)

        output = subprocess.run(['find', '/', '-name', 'redis.conf', '-type', 'f', '2>/dev/null'], capture_output=True, text=True, timeout=30)

        if output.returncode == 0:
            found_paths = [line.strip() for line in output.stdout.split('\n') if line.strip()]
            config_paths.extend(found_paths)

        config_paths = sorted(set(config_paths))

    except Exception as e:
        logger.error(f'查找Redis配置文件失败: {str(e)}')

    return config_paths
def analyze_redis_config(cfg_filepath):
    """
    解析Redis配置文件
    """
    cfg_state = {}

    try:
        if not os.path.exists(cfg_filepath):
            return cfg_state

        with open(cfg_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()

                if key in ['dir', 'dbfilename', 'appendfilename', 'logfile', 'pidfile', 'unixsocket']:
                    cfg_state[key] = val

            elif ' ' in line:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    key, val = parts
                    key = key.strip()
                    val = val.strip()

                    if key in ['dir', 'dbfilename', 'appendfilename', 'logfile', 'pidfile', 'unixsocket']:
                        cfg_state[key] = val

    except Exception as e:
        logger.error(f'解析Redis配置文件失败: {str(e)}')

    return cfg_state
def fetch_redis_install_path(pid):
    """
    获取Redis安装路径
    """
    install_info = {}

    try:
        exe_path = f'/proc/{pid}/exe'
        if os.path.exists(exe_path):
            output = subprocess.run(['readlink', '-f', exe_path], capture_output=True, text=True)

            if output.returncode == 0:
                install_info['可执行文件'] = output.stdout.strip()

                redis_dir = os.path.dirname(output.stdout.strip())
                install_info['安装目录'] = redis_dir

                redis_root = os.path.dirname(redis_dir)
                install_info['根目录'] = redis_root

        cwd_path = f'/proc/{pid}/cwd'
        if os.path.exists(cwd_path):
            output = subprocess.run(['readlink', '-f', cwd_path], capture_output=True, text=True)

            if output.returncode == 0:
                install_info['工作目录'] = output.stdout.strip()

        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'dir'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'dir' and i + 1 < len(lines):
                    install_info['数据目录'] = lines[i + 1].strip()
                    break

        output = subprocess.run(['which', 'redis-server'], capture_output=True, text=True)

        if output.returncode == 0:
            install_info['命令路径'] = output.stdout.strip()

        output = subprocess.run(['which', 'redis-cli'], capture_output=True, text=True)

        if output.returncode == 0:
            install_info['CLI路径'] = output.stdout.strip()

    except Exception as e:
        logger.error(f'获取Redis安装路径失败: {str(e)}')

    return install_info
def fetch_redis_config_path(pid):
    """
    获取Redis配置文件路径
    """
    cfg_state = {}

    try:
        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', '*'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'config_file' and i + 1 < len(lines):
                    cfg_filepath = lines[i + 1].strip()
                    cfg_state['配置文件'] = cfg_filepath

                    if os.path.exists(cfg_filepath):
                        cfg_state['配置文件状态'] = '存在'
                        cfg_state['配置文件大小'] = f"{os.path.getsize(cfg_filepath)} 字节"

                        stat_info = os.stat(cfg_filepath)
                        mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        cfg_state['修改时间'] = mtime
                    else:
                        cfg_state['配置文件状态'] = '不存在'
                    break

        cmdline_path = f'/proc/{pid}/cmdline'
        if os.path.exists(cmdline_path):
            with open(cmdline_path, 'r') as f:
                cmdline = f.read().replace('\x00', ' ')

            config_match = re.search(r'--?\s*config\s+file\s*=?\s*([^\s]+)', cmdline)  # NOSONAR
            if config_match:
                cfg_state['命令行配置文件'] = config_match.group(1)

        output = subprocess.run(['ps', '-p', pid, '-o', 'args='], capture_output=True, text=True)

        if output.returncode == 0:
            cmdline = output.stdout.strip()
            config_match = re.search(r'--?\s*config\s+file\s*=?\s*([^\s]+)', cmdline)  # NOSONAR
            if config_match:
                cfg_state['进程配置文件'] = config_match.group(1)

    except Exception as e:
        logger.error(f'获取Redis配置文件路径失败: {str(e)}')

    return cfg_state
def fetch_redis_persistence_path(pid):
    """
    获取Redis持久化文件路径
    """
    persistence_info = {}

    try:
        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'dir'], capture_output=True, text=True, timeout=5)

        data_dir = None
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'dir' and i + 1 < len(lines):
                    data_dir = lines[i + 1].strip()
                    persistence_info['数据目录'] = data_dir
                    break

        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'dbfilename'], capture_output=True, text=True, timeout=5)

        rdb_filename = None
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'dbfilename' and i + 1 < len(lines):
                    rdb_filename = lines[i + 1].strip()
                    persistence_info['RDB文件名'] = rdb_filename
                    break

        if data_dir and rdb_filename:
            rdb_path = os.path.join(data_dir, rdb_filename)
            persistence_info['RDB文件路径'] = rdb_path

            if os.path.exists(rdb_path):
                persistence_info['RDB文件状态'] = '存在'
                persistence_info['RDB文件大小'] = f"{os.path.getsize(rdb_path)} 字节"

                stat_info = os.stat(rdb_path)
                mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                persistence_info['RDB修改时间'] = mtime
            else:
                persistence_info['RDB文件状态'] = '不存在'

        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'appendfilename'], capture_output=True, text=True, timeout=5)

        aof_filename = None
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'appendfilename' and i + 1 < len(lines):
                    aof_filename = lines[i + 1].strip()
                    persistence_info['AOF文件名'] = aof_filename
                    break

        if data_dir and aof_filename:
            aof_path = os.path.join(data_dir, aof_filename)
            persistence_info['AOF文件路径'] = aof_path

            if os.path.exists(aof_path):
                persistence_info['AOF文件状态'] = '存在'
                persistence_info['AOF文件大小'] = f"{os.path.getsize(aof_path)} 字节"

                stat_info = os.stat(aof_path)
                mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                persistence_info['AOF修改时间'] = mtime
            else:
                persistence_info['AOF文件状态'] = '不存在'

        output = subprocess.run(['redis-cli', 'INFO', 'persistence'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for line in lines:
                if line.startswith('rdb_last_save_time:'):
                    save_time = datetime.fromtimestamp(int(line.split(':')[1])).strftime('%Y-%m-%d %H:%M:%S')
                    persistence_info['RDB最后保存时间'] = save_time
                elif line.startswith('rdb_last_bgsave_status:'):
                    persistence_info['RDB最后保存状态'] = line.split(':')[1]
                elif line.startswith('aof_last_rewrite_status:'):
                    persistence_info['AOF最后重写状态'] = line.split(':')[1]
                elif line.startswith('aof_last_rewrite_time_sec:'):
                    persistence_info['AOF最后重写耗时'] = f"{line.split(':')[1]} 秒"

    except Exception as e:
        logger.error(f'获取Redis持久化文件路径失败: {str(e)}')

    return persistence_info
def fetch_redis_log_path(pid):
    """
    获取Redis日志文件路径
    """
    log_info = {}

    try:
        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'logfile'], capture_output=True, text=True, timeout=5)

        log_file = None
        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'logfile' and i + 1 < len(lines):
                    log_file = lines[i + 1].strip()
                    log_info['日志文件'] = log_file
                    break

        if log_file and log_file != 'stdout' and log_file != '':
            if os.path.exists(log_file):
                log_info['日志文件状态'] = '存在'
                log_info['日志文件大小'] = f"{os.path.getsize(log_file)} 字节"

                stat_info = os.stat(log_file)
                mtime = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                log_info['日志修改时间'] = mtime
            else:
                log_info['日志文件状态'] = '不存在'
        elif log_file == 'stdout':
            log_info['日志输出'] = '标准输出'
        elif log_file == '':
            log_info['日志输出'] = '未配置'

        output = subprocess.run(['redis-cli', 'CONFIG', 'GET', 'loglevel'], capture_output=True, text=True, timeout=5)

        if output.returncode == 0:
            lines = output.stdout.split('\n')
            for i in range(0, len(lines) - 1):
                if lines[i].strip() == 'loglevel' and i + 1 < len(lines):
                    log_info['日志级别'] = lines[i + 1].strip()
                    break

        common_log_paths = [
            '/var/log/redis/redis-server.log',
            '/var/log/redis.log',
            '/var/log/redis/redis.log',
            '/usr/local/var/log/redis.log',
            '/opt/redis/logs/redis.log'
        ]

        for path in common_log_paths:
            if os.path.exists(path):
                if '日志文件' not in log_info:
                    log_info['日志文件'] = path
                    log_info['日志文件状态'] = '存在'
                    log_info['日志文件大小'] = f"{os.path.getsize(path)} 字节"
                    break

    except Exception as e:
        logger.error(f'获取Redis日志文件路径失败: {str(e)}')

    return log_info

TOOL_CONFIG = {
    "name": "fetch_redis_base_path",
    "function": fetch_redis_base_path,
    "description": "采集Redis安装路径、配置文件路径、持久化文件路径（RDB/AOF）、日志文件路径",
    "parameters": {
        "type": "object",
        "properties": {
            "path_type": {
                "type": "string",
                "description": "指定要采集的路径类型，可选值：install（安装路径）、config（配置文件路径）、persistence（持久化文件路径）、log（日志文件路径）、all（所有路径信息）",
                "enum": ["install", "config", "persistence", "log", "all"]
            }
        },
        "required": []
    }
}
