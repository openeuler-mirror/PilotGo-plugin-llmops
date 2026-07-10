import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_sched')

def fetch_proc_sched(pid):
    """Read /proc/<pid>/sched showing scheduler statistics for a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Scheduler statistics string
    """
    try:
        pid = str(int(pid))
        path = f'/proc/{pid}/sched'
        if not os.path.exists(path):
            return f'Error: process {pid} not found or sched not available'
        with open(path) as f:
            content = f.read().strip()
        if not content:
            return f'No scheduler info for PID {pid}'
        return f'=== Scheduler Info for PID {pid} ===\n{content}'
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/sched'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_sched",
    "function": fetch_proc_sched,
    "description": "Read scheduler statistics for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
