import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_smaps')

def fetch_proc_smaps(pid, summary=None):
    """Read /proc/<pid>/smaps showing detailed memory info for a process.

    Args:
        pid: Target PID (e.g. "1234")
        summary: If "true", show only rollup summary

    Returns:
        Memory details string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        path = f'/proc/{pid}/smaps'
        if not os.path.exists(path):
            path2 = f'/proc/{pid}/smaps_rollup'
            if os.path.exists(path2):
                with open(path2) as f:
                    return f'=== SMAPS Rollup for PID {pid} ===\n{f.read().strip()}'
            return f'Error: process {pid} not found'
        with open(path) as f:
            content = f.read()
        if summary and summary.lower() in ('true', '1', 'yes'):
            path2 = f'/proc/{pid}/smaps_rollup'
            if os.path.exists(path2):
                with open(path2) as f:
                    return f'=== SMAPS Rollup for PID {pid} ===\n{f.read().strip()}'
        lines = content.strip().split('\n')
        out = [f'=== SMAPS for PID {pid} (first 300 lines) ===']
        for line in lines[:300]:
            out.append(line)
        if len(lines) > 300:
            out.append(f'\n... truncated, {len(lines)} lines total')
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
    "name": "fetch_proc_smaps",
    "function": fetch_proc_smaps,
    "description": "Read detailed memory maps (smaps) for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"},
            "summary": {"type": "string", "description": "Set 'true' for rollup summary only"}
        },
        "required": ["pid"]
    }
}
