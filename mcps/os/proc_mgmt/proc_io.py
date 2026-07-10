import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_io')

def fetch_proc_io(pid):
    """Read /proc/<pid>/io showing I/O statistics for a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        I/O statistics string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/io'
        if not os.path.exists(path):
            return f'Error: process {pid} not found or I/O not available'
        with open(path) as f:
            content = f.read().strip()
        if not content:
            return f'No I/O stats for PID {pid}'
        return f'=== I/O Stats for PID {pid} ===\n{content}'
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/io'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_io",
    "function": fetch_proc_io,
    "description": "Read I/O statistics for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
