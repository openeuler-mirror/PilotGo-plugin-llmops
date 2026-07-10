import logging
import os
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_uptime')

def fetch_proc_uptime(pid=None):
    """Show system uptime and optionally process uptime.

    Args:
        pid: Optional PID to show process-specific uptime

    Returns:
        System and process uptime information
    """
    try:
        with open('/proc/uptime') as f:
            content = f.read().strip()
        parts = content.split()
        if len(parts) < 2:
            return f'Error: cannot read /proc/uptime'
        uptime_secs = float(parts[0])
        idle_secs = float(parts[1])
        out = ['=== System Uptime ===']

        boot_time = time.time() - uptime_secs
        out.append(f'Boot time:  {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time))}')
        days = int(uptime_secs // 86400)
        hours = int((uptime_secs % 86400) // 3600)
        minutes = int((uptime_secs % 3600) // 60)
        out.append(f'Uptime:     {days}d {hours}h {minutes}m')
        out.append(f'Idle time:  {idle_secs:.0f}s ({idle_secs/uptime_secs*100:.1f}%)' if uptime_secs > 0 else 'Idle: N/A')

        if pid is not None:
            pid = int(pid)
            if pid <= 0:
                return f'Error: invalid PID {pid}'
            pp = f'/proc/{pid}'
            if not os.path.exists(pp):
                return f'Error: process {pid} not found'
            out.append(f'\n=== Process {pid} Uptime ===')
            ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
            elapsed = 0
            with open(f'{pp}/stat') as f:
                st = f.read().strip()
            end = st.rfind(')')
            fields = st[end+2:].split()
            if len(fields) > 19:
                start_ticks = int(fields[19])
                proc_start = boot_time + start_ticks / ticks
                out.append(f'Started:    {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(proc_start))}')
                elapsed = time.time() - proc_start
                ed = int(elapsed//86400); eh = int((elapsed%86400)//3600)
                em = int((elapsed%3600)//60); es = int(elapsed%60)
                out.append(f'Elapsed:    {ed}d {eh}h {em}m {es}s')
            if len(fields) > 13:
                ut = int(fields[11])/ticks; st = int(fields[12])/ticks
                out.append(f'User CPU:   {ut:.2f}s')
                out.append(f'System CPU: {st:.2f}s')
                if elapsed > 0:
                    out.append(f'Avg CPU:    {(ut+st)/elapsed*100:.2f}%')

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
    "name": "fetch_proc_uptime",
    "function": fetch_proc_uptime,
    "description": "Show system uptime and optionally process uptime with CPU stats",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Optional PID for process uptime"}
        },
        "required": []
    }
}
