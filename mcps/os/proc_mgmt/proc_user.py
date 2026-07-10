import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_user')

def fetch_proc_user(user, sort_by=None):
    """List processes for a specific user.

    Args:
        user: Username (e.g. "root", "www-data")
        sort_by: Sort by 'cpu' or 'mem'

    Returns:
        User's processes listing
    """
    try:
        if not user:
            return 'Error: user parameter is required'
        sort = None
        if sort_by == 'mem':
            sort = '-%mem'
        elif sort_by == 'cpu':
            sort = '-%cpu'
        cmd = ['ps', '-u', user, '-o', 'pid,%cpu,%mem,vsz,comm', '--no-headers']
        if sort:
            cmd.append(f'--sort={sort}')
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: user "{user}" may not exist or ps failed: {result.stderr}'
        lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
        out = [f'=== Processes for user: {user} ===']
        out.append(f'{"PID":>7} {"%CPU":>6} {"%MEM":>6} {"VSZ":>10} COMMAND')
        out.append('-' * 60)
        total_cpu = 0.0
        for l in lines:
            p = l.split()
            if len(p) >= 5:
                try:
                    total_cpu += float(p[1])
                except ValueError:
                    pass
                out.append(f'{p[0]:>7} {p[1]:>6} {p[2]:>6} {p[3]:>10} {p[4][:35]}')
        out.append(f'\nProcesses: {len(lines)}  Total CPU: {total_cpu:.1f}%')
        return '\n'.join(out)
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
# - Invalid or non-existent username
# - ps command unavailable or failed
# - Empty result set

TOOL_CONFIG = {
    "name": "fetch_proc_user",
    "function": fetch_proc_user,
    "description": "List processes for a specific user",
    "parameters": {
        "type": "object",
        "properties": {
            "user": {"type": "string", "description": "Username, e.g. 'root'"},
            "sort_by": {"type": "string", "description": "Sort by 'cpu' or 'mem'"}
        },
        "required": ["user"]
    }
}
