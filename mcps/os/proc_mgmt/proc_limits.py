import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_limits')

def fetch_proc_limits(pid):
    """Read /proc/<pid>/limits showing resource limits for a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Resource limits string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/limits'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path) as f:
            content = f.read()
        return f'=== Resource Limits for PID {pid} ===\n{content.strip()}'
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/limits'
    except PermissionError as e:
        logger.error(f'Permission denied: {e}')
        return f'Permission denied: {e}'
    except FileNotFoundError as e:
        logger.error(f'Resource not found: {e}')
        return f'Resource not found: {e}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_limits",
    "function": fetch_proc_limits,
    "description": "Read resource limits for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
