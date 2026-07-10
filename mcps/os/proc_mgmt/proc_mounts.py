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
        for line in lines:
            parts = line.split()
            if len(parts) >= 4:
                if target and target not in line:
                    continue
                out.append(f'{parts[0]:<20} {parts[1]:<25} {parts[2]:<10} {parts[3]}')
                count += 1
        out.append(f'\nTotal: {count} mounts')
        return '\n'.join(out)
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

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
