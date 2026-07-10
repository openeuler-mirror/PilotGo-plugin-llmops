import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_mounts')

def fetch_proc_mounts(target=None):
    """Read /proc/mounts showing mounted filesystems.

    Args:
        target: Optional filter string (e.g. "/dev/sda" or "tmpfs")

    Returns:
        Formatted mount information string
    """
    try:
        with open('/proc/mounts') as f:
            lines = f.readlines()
        out = ['=== Mounted Filesystems ===']
        out.append(f'{"Device":<20} {"Mount Point":<25} {"Type":<10} {"Options"}')
        out.append('-' * 80)
        count = 0
        type_stats = {}
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                if target and target not in line:
                    continue
                out.append(f'{parts[0]:<20} {parts[1]:<25} {parts[2]:<10} {parts[3]}')
                fstype = parts[2]
                type_stats[fstype] = type_stats.get(fstype, 0) + 1
                count += 1
        out.append(f'\nTotal: {count} mounts')
        if type_stats:
            out.append('Filesystem types:')
            for fs, cnt in sorted(type_stats.items()):
                out.append(f'  {fs}: {cnt}')
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
# - /proc filesystem unavailable
# - Empty mount table
# - Target filter with no matches

TOOL_CONFIG = {
    "name": "fetch_proc_mounts",
    "function": fetch_proc_mounts,
    "description": "List mounted filesystems with optional filter",
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Optional filter string, e.g. 'tmpfs'"}
        },
        "required": []
    }
}
