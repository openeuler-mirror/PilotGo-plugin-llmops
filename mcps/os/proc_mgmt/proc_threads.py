import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_threads')

def fetch_proc_threads(pid, fmt=None):
    """List threads of a process from /proc/<pid>/task/.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Thread listing with names
    """
    try:
        pid = str(int(pid))
        task_dir = f'/proc/{pid}/task'
        if not os.path.exists(task_dir):
            return f'Error: process {pid} not found'
        out = [f'=== Threads for PID {pid} ===']
        out.append(f'{"TID":>8}  NAME')
        out.append('-' * 40)
        count = 0
        states = {}
        for tid in sorted(os.listdir(task_dir), key=int):
            try:
                comm_path = f'{task_dir}/{tid}/comm'
                name = '?'
                if os.path.exists(comm_path):
                    with open(comm_path) as f:
                        name = f.read().strip()
                # Get thread state from stat
                thr_state = '?'
                stat_path = f'{task_dir}/{tid}/stat'
                if os.path.exists(stat_path):
                    with open(stat_path) as f:
                        sf = f.read().strip()
                    end = sf.rfind(')')
                    fs = sf[end+2:].split() if end > 0 else []
                    thr_state = fs[0] if fs else '?'
                out.append(f'{tid:>8}  {thr_state}  {name}')
                states[thr_state] = states.get(thr_state, 0) + 1
                count += 1
            except (OSError, ValueError):
                pass
        out.append(f'\nTotal: {count} threads')
        state_names = {'R': 'Running', 'S': 'Sleeping', 'D': 'Uninterruptible',
                       'Z': 'Zombie', 'T': 'Stopped', 't': 'Tracing'}
        out.append('State breakdown:')
        for s, cnt in sorted(states.items()):
            out.append(f'  {state_names.get(s, s)}({s}): {cnt}')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/task'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

TOOL_CONFIG = {
    "name": "fetch_proc_threads",
    "function": fetch_proc_threads,
    "description": "List threads of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "format": {"type": "string", "description": "Output: text/json/summary", "enum": ["text","json","summary"]}, "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
