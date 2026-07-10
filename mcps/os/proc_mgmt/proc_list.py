import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_list')

def fetch_proc_list(sort_by=None, limit=None):
    """List all running processes with optional sorting and limit.

    Args:
        sort_by: Sort field - cpu/mem/pid/user (default: pid)
        limit: Max processes to return (e.g. "20")

    Returns:
        Formatted process list string
    """
    try:
        if limit is not None:
            try:
                limit = int(limit)
                if limit <= 0:
                    return 'Error: limit must be a positive integer'
            except (ValueError, TypeError):
                return f'Error: limit must be an integer, got: {limit}'
        if sort_by and sort_by not in ('cpu', 'mem', 'pid', 'user'):
            return f'Error: unsupported sort field: {sort_by}'

        sort_map = {'cpu': '-%cpu', 'mem': '-%mem', 'pid': 'pid', 'user': 'user'}
        sort_arg = sort_map.get(sort_by, 'pid') if sort_by else 'pid'
        cmd = ['ps', 'aux', f'--sort={sort_arg}', '--no-headers']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error running ps: {result.stderr}'

        lines = result.stdout.strip().split('\n')
        if limit:
            lines = lines[:limit]

        out = ['=== Process List ===']
        out.append(f'{"USER":<10} {"PID":>7} {"%CPU":>5} {"%MEM":>5} {"VSZ":>8} {"RSS":>8} {"STAT":<5} {"COMMAND"}')
        out.append('-' * 90)
        for l in lines:
            p = l.split(None, 10)
            if len(p) >= 11:
                cmd = p[10][:60]
                out.append(f'{p[0]:<10} {p[1]:>7} {p[2]:>5} {p[3]:>5} {p[4]:>8} {p[5]:>8} {p[7]:<5} {cmd}')
        out.append(f'\nTotal: {len(lines)} processes')
        out.append('=' * 25)
        return '\n'.join(out)
    except PermissionError as e:
        logger.error(f'Permission denied: {e}')
        return f'Permission denied: {e}'
        logger.error(f'Permission denied: {e}')
        return f'Permission denied: {e}'
    except FileNotFoundError as e:
        logger.error(f'Resource not found: {e}')
        return f'Resource not found: {e}'
    except Exception as e:
        logger.error(f'Failed to list processes: {e}')
        return f'Failed to list processes: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

TOOL_CONFIG = {
    "name": "fetch_proc_list",
    "function": fetch_proc_list,
    "description": "List all running processes with optional sorting (cpu/mem/pid/user) and limit",
    "parameters": {
        "type": "object",
        "properties": {
            "sort_by": {"type": "string", "description": "Sort field: cpu/mem/pid/user", "enum": ["cpu", "mem", "pid", "user"]},
            "limit": {"type": "string", "description": "Max processes to return, e.g. '20'"}
        },
        "required": []
    }
}
