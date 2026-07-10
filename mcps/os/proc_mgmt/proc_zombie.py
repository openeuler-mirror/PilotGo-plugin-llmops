import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_zombie')

def fetch_proc_zombie():
    """Find zombie (defunct) processes on the system.

    Returns:
        List of zombie processes or confirmation of none found.
    """
    try:
        result = subprocess.run(['ps', 'aux', '--no-headers'], capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: ps failed: {result.stderr}'
        out = ['=== Zombie Processes (defunct) ===']
        count = 0
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split(None, 10)
            if len(parts) >= 8 and 'Z' in parts[7]:
                out.append(f'  PID:{parts[1]:>7}  PPID:{parts[3]:>7}  {parts[10][:50] if len(parts)>10 else ""}')
                count += 1
        if count == 0:
            out.append('No zombie processes found.')
        else:
            out.append(f'\nFound: {count} zombie process(es)')
        return '\n'.join(out)
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

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
