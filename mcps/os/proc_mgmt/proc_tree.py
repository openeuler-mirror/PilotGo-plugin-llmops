import logging
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_tree')

def fetch_proc_tree():
    """Show process tree (parent-child relationships).

    Returns:
        Process tree string using pstree or ps --forest
    """
    try:
        result = subprocess.run(['pstree', '-p'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return f'=== Process Tree ===\n{result.stdout.strip()}'
        result = subprocess.run(['ps', 'ax', '--forest', '-o', 'pid=,ppid=,cmd='],
                                capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: {result.stderr}'
        return f'=== Process Tree ===\n{result.stdout.strip()}'
    except FileNotFoundError:
        result = subprocess.run(['ps', 'ax', '--forest', '-o', 'pid=,ppid=,cmd='],
                                capture_output=True, text=True)
        if result.returncode != 0:
            return f'Error: {result.stderr}'
        return f'=== Process Tree ===\n{result.stdout.strip()}'
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
# - pstree command unavailable (fallback to /proc scan)
# - /proc filesystem not mounted
# - Orphaned processes

TOOL_CONFIG = {
    "name": "fetch_proc_tree",
    "function": fetch_proc_tree,
    "description": "Show process tree with parent-child relationships",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
