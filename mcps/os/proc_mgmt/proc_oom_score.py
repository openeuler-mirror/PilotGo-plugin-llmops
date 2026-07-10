import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_oom_score')

def fetch_proc_oom_score(pid):
    """Read OOM (Out-Of-Memory) scores for a process.

    Args:
        pid: Target PID (e.g. "1234")

    Returns:
        OOM score and adjust information string
    """
    try:
        pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        proc_dir = f'/proc/{pid}'
        if not os.path.exists(proc_dir):
            return f'Error: process {pid} not found'
        out = [f'=== OOM Scores for PID {pid} ===']
        for fname in ('oom_score', 'oom_score_adj', 'oom_adj'):
            path = os.path.join(proc_dir, fname)
            if os.path.exists(path):
                with open(path) as f:
                    out.append(f'{fname}: {f.read().strip()}')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except PermissionError:
        return f'Permission denied reading OOM scores for PID {pid}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_oom_score",
    "function": fetch_proc_oom_score,
    "description": "Read OOM scores for a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"}
        },
        "required": ["pid"]
    }
}
