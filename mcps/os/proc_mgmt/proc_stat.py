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
        lparen = raw.find('(')
        rparen = raw.find(')', lparen) if lparen >= 0 else -1
        if lparen == -1 or rparen == -1:
            return f'Error: malformed stat for PID {pid}'
        pid_str = raw[:lparen-1] if lparen > 0 else raw[:lparen]
        comm = raw[lparen:rparen+1]
        fields = [pid_str] + [comm] + raw[rparen+2:].split()
        out = [f'=== Process Stat for PID {pid} ===']
        for i, (name, val) in enumerate(zip(STAT_FIELDS, fields)):
            out.append(f'  {name:<14} {val}')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError as e:
        logger.error(f'Permission denied: {e}')
        return f'Permission denied: {e}'
    except FileNotFoundError as e:
        logger.error(f'Resource not found: {e}')
        return f'Resource not found: {e}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

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
