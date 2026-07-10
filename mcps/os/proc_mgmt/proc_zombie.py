import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_zombie')

def fetch_proc_zombie():
    """Find zombie (defunct) processes on the system.

    Returns:
        List of zombie processes or confirmation of none found.
    """
    try:
        result = subprocess.run(['ps', '-eo', 'pid,ppid,stat,comm', '--no-headers'], capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: ps failed: {result.stderr}'
        out = ['=== Zombie Processes (defunct) ===']
        count = 0
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(None, 3)
            if len(parts) >= 3 and 'Z' in parts[2]:
                pid = parts[0]
                ppid = parts[1]
                pname = parts[3][:50] if len(parts) > 3 else ''
                ppname = ''
                try:
                    with open(f'/proc/{ppid}/comm') as f:
                        ppname = f.read().strip()
                except (OSError, FileNotFoundError):
                    ppname = '(exited)'
                out.append(f'  PID:{pid:>7}  PPID:{ppid:>7}({ppname})  {pname}')
                count += 1
        if count == 0:
            out.append('No zombie processes found.')
        else:
            out.append(f'\nFound: {count} zombie process(es)')
            out.append('Tip: zombies persist until parent calls wait(). Restart or kill the parent process.')
        return '\n'.join(out)
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

TOOL_CONFIG = {
    "name": "fetch_proc_zombie",
    "function": fetch_proc_zombie,
    "description": "Find zombie (defunct) processes",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
