import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_net')

NET_FILES = ['arp', 'dev', 'route', 'tcp', 'tcp6', 'udp', 'udp6', 'unix']

def fetch_proc_net(category=None):
    """Read network info from /proc/net/ (arp, dev, route, tcp, etc.).

    Args:
        category: Sub-file to read (default: 'dev'), e.g. 'tcp', 'route'

    Returns:
        Network information string
    """
    try:
        if category and category not in NET_FILES:
            return f'Error: unknown category: {category}. Valid: {", ".join(NET_FILES)}'
        cat = category or 'dev'
        path = f'/proc/net/{cat}'
        if not os.path.exists(path):
            return f'Error: /proc/net/{cat} not found'
        with open(path) as f:
            content = f.read().strip()
        if not content:
            return f'No data in /proc/net/{cat}'
        return f'=== /proc/net/{cat} ===\n{content}'
    except PermissionError as e:
        logger.error(f'Permission denied: {e}')
        return f'Permission denied reading /proc/net/{cat}'
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
# - Missing ss command
# - /proc/net/ inaccessible
# - Permission denied on network info

TOOL_CONFIG = {
    "name": "fetch_proc_net",
    "function": fetch_proc_net,
    "description": "Read network statistics from /proc/net/",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "File to read: arp/dev/route/tcp/tcp6/udp/udp6/unix"}
        },
        "required": []
    }
}
