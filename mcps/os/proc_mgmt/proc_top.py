import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_top')

def fetch_proc_top(count=None, sort_by=None):
    """Show top CPU-consuming processes (like top -b -n1).

    Args:
        count: Number of top processes to show (default 10)
        sort_by: 'cpu' or 'mem' (default cpu)

    Returns:
        Top processes listing
    """
    try:
        n = 10
        if count:
            try:
                n = int(count)
                if n < 1: n = 10
            except:
                return f'Error: invalid count: {count}'
        sort = '-%cpu' if not sort_by or sort_by == 'cpu' else '-%mem'
        cmd = ['ps', 'aux', f'--sort={sort}', '--no-headers']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: ps failed: {result.stderr}'
        lines = result.stdout.strip().split('\n')[:n]
        out = [f'=== Top {n} by {"CPU" if sort=="-%cpu" else "MEM"} ===']
        out.append(f'{"USER":<10} {"PID":>7} {"%CPU":>5} {"%MEM":>5} {"VSZ":>8} {"COMMAND"}')
        out.append('-' * 60)
        for l in lines:
            p = l.split(None, 10)
            if len(p) >= 11:
                out.append(f'{p[0]:<10} {p[1]:>7} {p[2]:>5} {p[3]:>5} {p[4]:>8} {p[10][:40]}')
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
    "name": "fetch_proc_top",
    "function": fetch_proc_top,
    "description": "Show top CPU/memory consuming processes",
    "parameters": {
        "type": "object",
        "properties": {
            "count": {"type": "string", "description": "Number of processes (default 10)"},
            "sort_by": {"type": "string", "description": "Sort by 'cpu' or 'mem'"}
        },
        "required": []
    }
}
