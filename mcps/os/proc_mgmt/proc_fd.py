import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_fd')

def fetch_proc_fd(pid):
    """List open file descriptors of a process from /proc/<pid>/fd/.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        List of file descriptors with their targets
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        fd_dir = f'/proc/{pid}/fd'
        if not os.path.exists(fd_dir):
            return f'Error: process {pid} not found'
        out = [f'=== Open FDs for PID {pid} ===']
        count = 0
        for entry in sorted(os.listdir(fd_dir), key=lambda x: int(x)):
            link = os.path.join(fd_dir, entry)
            try:
                target = os.readlink(link)
                out.append(f'  fd {entry:>4} -> {target}')
                count += 1
            except OSError:
                out.append(f'  fd {entry:>4} -> (unreachable)')
                count += 1
        out.append(f'\nTotal: {count} file descriptors')
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
    "name": "fetch_proc_fd",
    "function": fetch_proc_fd,
    "description": "List open file descriptors of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
