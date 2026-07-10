import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_env')

def fetch_proc_env(pid):
    """Read /proc/<pid>/environ showing environment variables of a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Environment variables string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/environ'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path, 'rb') as f:
            raw = f.read()
        if not raw:
            return f'PID {pid}: no environment variables'
        out = [f'=== Environment for PID {pid} ===']
        for entry in raw.split(b'\x00'):
            if entry:
                out.append(entry.decode('utf-8', errors='replace'))
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
    "name": "fetch_proc_env",
    "function": fetch_proc_env,
    "description": "Read environment variables of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
