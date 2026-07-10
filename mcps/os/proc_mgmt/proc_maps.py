import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_maps')

def fetch_proc_maps(pid):
    """Read /proc/<pid>/maps showing memory mappings of a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        Memory mappings string (first 200 lines)
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/maps'
        if not os.path.exists(path):
            return f'Error: process {pid} not found'
        with open(path) as f:
            lines = f.readlines()
        out = [f'=== Memory Maps for PID {pid} ===']
        max_lines = 200
        for i, line in enumerate(lines[:max_lines]):
            out.append(line.rstrip())
        if len(lines) > max_lines:
            out.append(f'\n... and {len(lines) - max_lines} more entries')
        out.append(f'\nTotal: {len(lines)} memory regions')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading /proc/{pid}/maps'
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
    "name": "fetch_proc_maps",
    "function": fetch_proc_maps,
    "description": "Read memory mappings of a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
