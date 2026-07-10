import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_cmdline')

def fetch_proc_cmdline(pid):
    """Read /proc/<pid>/cmdline showing the full command line of a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Command line string with arguments
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/cmdline'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path, 'rb') as f:
            raw = f.read()
        if not raw:
            return f'PID {pid}: empty cmdline (kernel thread)'
        args = raw.replace(b'\x00', b' ').decode('utf-8', errors='replace').strip()
        return f'=== Cmdline for PID {pid} ===\n{args}'
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/cmdline'
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
    "name": "fetch_proc_cmdline",
    "function": fetch_proc_cmdline,
    "description": "Read the command line of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
