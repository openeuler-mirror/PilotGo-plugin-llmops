import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_threads')

def fetch_proc_threads(pid):
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
        for tid in sorted(os.listdir(task_dir), key=int):
            try:
                comm_path = f'{task_dir}/{tid}/comm'
                name = '?'
                if os.path.exists(comm_path):
                    with open(comm_path) as f:
                        name = f.read().strip()
                out.append(f'{tid:>8}  {name}')
                count += 1
            except (OSError, ValueError):
                pass
        out.append(f'\nTotal: {count} threads')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/task'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_threads",
    "function": fetch_proc_threads,
    "description": "List threads of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
