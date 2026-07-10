import logging
import os
import signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('proc_kill')

def fetch_proc_kill(pid, sig=None):
    """Send a signal to a process (default: SIGTERM).

    Args:
        pid: Target PID (e.g. "1234")
        sig: Signal name or number (e.g. "9" or "SIGKILL")

    Returns:
        Result string
    """
    try:
        pid = int(pid)
        if pid <= 0:
            return f'Error: invalid PID {pid} (must be positive)'
        sig_desc = {}
        if sig is None:
            sig_name = 'SIGTERM'
            sig_num = signal.SIGTERM
        else:
            sig = str(sig).upper().replace('SIG', '')
            signal_aliases = {
                'TERM': signal.SIGTERM, 'KILL': signal.SIGKILL, 'HUP': signal.SIGHUP,
                'STOP': signal.SIGSTOP, 'CONT': signal.SIGCONT, 'INT': signal.SIGINT,
                'USR1': signal.SIGUSR1, 'USR2': signal.SIGUSR2, 'QUIT': signal.SIGQUIT,
                '1': signal.SIGHUP, '9': signal.SIGKILL, '15': signal.SIGTERM,
                '17': signal.SIGSTOP, '18': signal.SIGCONT, '2': signal.SIGINT,
            }
            sig_desc = {
                'TERM': 'Terminate gracefully', 'KILL': 'Force kill (cannot be caught)',
                'HUP': 'Hangup / reload config', 'STOP': 'Pause process',
                'CONT': 'Resume paused process', 'INT': 'Interrupt (Ctrl+C)',
                'USR1': 'User-defined signal 1', 'USR2': 'User-defined signal 2',
                'QUIT': 'Quit with core dump',
            }
            if sig in signal_aliases:
                sig_num = signal_aliases[sig]
                sig_name = sig if sig in sig_desc else f'SIG{sig}'
            else:
                return f'Error: unknown signal: {sig}. Supported: TERM KILL HUP STOP CONT INT USR1 USR2 QUIT or numbers 1 2 9 15 17 18'
        if not os.path.exists(f'/proc/{pid}'):
            return f'Error: process {pid} not found'
        os.kill(pid, sig_num)
        desc = sig_desc.get(sig_name.replace('SIG',''), '')
        return f'Signal {sig_name}({sig_num}) sent to PID {pid}. {desc}'
    except ProcessLookupError:
        return f'Error: process {pid} not found or already exited'
    except PermissionError:
        return f'Permission denied: cannot signal PID {pid} (may need root or own the process)'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

# Edge cases handled:
# - Invalid or non-existent PID
# - /proc filesystem unavailable
# - Permission denied for restricted /proc entries
# - Process exit between inspection steps

TOOL_CONFIG = {
    "name": "fetch_proc_kill",
    "function": fetch_proc_kill,
    "description": "Send a signal to a process",
    "parameters": {
        "type": "object",
        "properties": {
            "pid": {"type": "string", "description": "Target PID, e.g. '1234'"},
            "sig": {"type": "string", "description": "Signal: 9/KILL/TERM/HUP etc."}
        },
        "required": ["pid"]
    }
}
