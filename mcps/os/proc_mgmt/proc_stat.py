import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_stat')

STAT_FIELDS = ['pid', 'comm', 'state', 'ppid', 'pgrp', 'session', 'tty_nr', 'tpgid',
               'flags', 'minflt', 'cminflt', 'majflt', 'cmajflt', 'utime', 'stime',
               'cutime', 'cstime', 'priority', 'nice', 'num_threads', 'itrealvalue',
               'starttime', 'vsize', 'rss', 'rsslim']

def fetch_proc_stat(pid):
    """Read /proc/<pid>/stat showing process status in one line.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Parsed stat fields as key-value pairs
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/stat'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path) as f:
            raw = f.read().strip()
        name_end = raw.rfind(')')
        if name_end == -1:
            return f'Error: malformed stat for PID {pid}'
        head = raw[:name_end+1]
        tail = raw[name_end+2:]
        fields = [raw[:name_end].split('(', 1)[0]] + [head] + tail.split()
        out = [f'=== Process Stat for PID {pid} ===']
        for i, (name, val) in enumerate(zip(STAT_FIELDS, fields)):
            out.append(f'  {name:<14} {val}')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/stat'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_stat",
    "function": fetch_proc_stat,
    "description": "Read /proc/<pid>/stat with parsed fields",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
