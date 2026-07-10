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
        sort = '-%cpu' if sort_by == 'mem' else '-%cpu' if sort_by == 'cpu' else None
        cmd = ['ps', '-u', user, '--no-headers']
        if sort:
            cmd.append(f'--sort={sort}')
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: user "{user}" may not exist or ps failed: {result.stderr}'
        lines = result.stdout.strip().split('\n')
        out = [f'=== Processes for user: {user} ===']
        out.append(f'{"PID":>7} {"%CPU":>5} {"%MEM":>5} {"VSZ":>8} {"COMMAND"}')
        out.append('-' * 50)
        for l in lines:
            if not l.strip():
                continue
            p = l.split(None, 10)
            if len(p) >= 2:
                out.append(f'{p[0]:>7} {p[2] if len(p)>2 else "?":>5} {p[3] if len(p)>3 else "?":>5} {p[4] if len(p)>4 else "?":>8} {p[-1][:40]}')
        out.append(f'\nTotal: {len(lines)} processes')
        return '\n'.join(out)
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

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
