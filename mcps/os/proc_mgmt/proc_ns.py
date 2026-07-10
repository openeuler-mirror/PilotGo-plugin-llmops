import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_ns')

def fetch_proc_ns(pid):
    """List namespace references for a process from /proc/<pid>/ns/.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Namespace information string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        ns_dir = f'/proc/{pid}/ns'
        if not os.path.exists(ns_dir):
            return f'Error: process {pid} not found'
        out = [f'=== Namespaces for PID {pid} ===']
        for entry in sorted(os.listdir(ns_dir)):
            link = os.path.join(ns_dir, entry)
            try:
                target = os.readlink(link)
                out.append(f'  {entry:<12} -> {target}')
            except OSError:
                out.append(f'  {entry:<12} -> (unreachable)')
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
    "name": "fetch_proc_ns",
    "function": fetch_proc_ns,
    "description": "List namespace references for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
