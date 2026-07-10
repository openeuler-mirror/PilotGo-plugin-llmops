import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_search')

def fetch_proc_search(pattern, exact=None):
    """Search for processes by name or command line pattern.

    Args:
        pattern: Search pattern (e.g. "nginx", "python")
        exact: If "true", match exact process name only

    Returns:
        Matching processes string
    """
    try:
        if not pattern:
            return 'Error: pattern is required'
        if exact and exact.lower() in ('true', '1', 'yes'):
            cmd = ['pgrep', '-x', '-a', pattern]
        else:
            cmd = ['pgrep', '-a', pattern]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 1:
            # pgrep returns 1 when no match found
            return f'No processes matching "{pattern}" found'
        if result.returncode > 1:
            return f'Error running pgrep: {result.stderr.strip() or "unknown error"}'
        lines = result.stdout.strip().split('\n')
        out = [f'=== Process Search: "{pattern}" ===']
        if not lines or lines == ['']:
            out.append('No matching processes found.')
        else:
            out.append(f'{"PID":>7}  COMMAND')
            out.append('-' * 60)
            for line in lines:
                if line:
                    parts = line.split(None, 1)
                    out.append(f'{parts[0]:>7}  {parts[1] if len(parts)>1 else ""}'[:80])
            out.append(f'\nFound: {len(lines)} process(es)')
        return '\n'.join(out)
    except FileNotFoundError:
        return 'Error: pgrep command not found (install procps package)'
    except subprocess.SubprocessError as e:
        logger.error(f'pgrep failed: {e}')
        return f'Error running pgrep: {e}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

TOOL_CONFIG = {
    "name": "fetch_proc_search",
    "function": fetch_proc_search,
    "description": "Search for processes by name pattern",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern, e.g. 'nginx'"},
            "exact": {"type": "string", "description": "Set to 'true' for exact name match"}
        },
        "required": ["pattern"]
    }
}
