import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_cgroup')

def fetch_proc_cgroup(pid):
    """Read /proc/<pid>/cgroup control group info for a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Formatted cgroup information string
    """
    try:

    if pid is not None:
        try:
            pid = int(pid)
            if pid <= 0: return f'Invalid PID: {pid}'
        except (ValueError,TypeError): return f'PID must be integer'
        pid = str(int(pid))
        path = f'/proc/{pid}/cgroup'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path) as f:
            content = f.read().strip()
        if not content:
            return 'No cgroup entries found.'
        out = [f'=== Cgroups for PID {pid} ===']
        for line in content.split('\n'):
            parts = line.split(':', 2)
            if len(parts) == 3:
                out.append(f'Hierarchy {parts[0]:>2}  {parts[1]:<20}  {parts[2]}')
            else:
                out.append(line)
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
    "name": "fetch_proc_cgroup",
    "function": fetch_proc_cgroup,
    "description": "Read control group info for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
