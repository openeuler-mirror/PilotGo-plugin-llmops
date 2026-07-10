import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_status')

def fetch_proc_status(pid):
    """Read /proc/<pid>/status showing human-readable process status.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Process status key-value pairs
    """
    try:
        pid = str(int(pid))
        path = f'/proc/{pid}/status'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path) as f:
            content = f.read().strip()
        return f'=== Process Status for PID {pid} ===\n{content}'
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/status'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_status",
    "function": fetch_proc_status,
    "description": "Read human-readable process status",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
