import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_info')

def fetch_proc_info(pid=None):
    """Get detailed info for a process or list all processes.

    Args:
        pid: Optional target PID (e.g. "1234")

    Returns:
        Process information string
    """
    try:
        if pid:
            pid = str(int(pid))
        if int(pid) <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
            path = f'/proc/{pid}/status'
            if not os.path.exists(path):
                return f'Error: process {pid} not found'
            with open(path) as f:
                content = f.read()
            return f'=== Status for PID {pid} ===\n{content.strip()}'
        result = subprocess.run(['ps', 'aux', '--no-headers'], capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: ps failed: {result.stderr}'
        lines = result.stdout.strip().split('\n')
        out = [f'{"USER":<10} {"PID":>7} {"%CPU":>5} {"%MEM":>5} {"VSZ":>8} {"COMMAND"}', '-'*60]
        for l in lines:
            p = l.split(None, 10)
            if len(p) >= 11:
                out.append(f'{p[0]:<10} {p[1]:>7} {p[2]:>5} {p[3]:>5} {p[4]:>8} {p[10][:40]}')
        out.append(f'\nTotal: {len(lines)} processes')
        return '\n'.join(out)
    except ValueError:
        return f'Error: invalid PID: {pid}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_info",
    "function": fetch_proc_info,
    "description": "Get detailed process info or list all processes",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Optional target PID, e.g. '1234'"}
        },
        "required": []
    }
}
