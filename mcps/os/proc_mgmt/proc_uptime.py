import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_uptime')

def fetch_proc_uptime():
    """Read /proc/uptime showing system uptime in seconds.

    Returns:
        System uptime information string
    """
    try:
        with open('/proc/uptime') as f:
            content = f.read().strip()
        parts = content.split()
        if len(parts) >= 2:
            uptime = float(parts[0])
            idle = float(parts[1])
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            minutes = int((uptime % 3600) // 60)
            out = ['=== System Uptime ===']
            out.append(f'Uptime:    {days}d {hours}h {minutes}m ({uptime:.2f} seconds)')
            out.append(f'Idle time: {idle:.2f} seconds')
            out.append(f'Idle%:     {idle/uptime*100:.1f}%' if uptime > 0 else 'Idle%: N/A')
            return '\n'.join(out)
        return f'=== System Uptime ===\nRaw: {content}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

TOOL_CONFIG = {
    "name": "fetch_proc_uptime",
    "function": fetch_proc_uptime,
    "description": "Show system uptime from /proc/uptime",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
