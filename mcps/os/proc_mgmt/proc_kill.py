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
        if sig is None:
            sig_name = 'SIGTERM'
            sig_num = signal.SIGTERM
        else:
            sig = str(sig).upper().replace('SIG', '')
            sig_map = {str(v): k for k, v in signal.Signals.__members__.items()}
            valid = {s: getattr(signal, s, None) for s in signal.Signals.__members__}
            if sig in valid:
                sig_num = valid[sig]
                sig_name = f'SIG{sig}'
            elif sig in sig_map:
                sig_num = int(sig)
                sig_name = sig_map[sig]
            else:
                return f'Error: unknown signal: {sig}'
        if not os.path.exists(f'/proc/{pid}'):
            return f'Error: process {pid} not found'
        os.kill(pid, sig_num)
        return f'Signal {sig_name} sent to PID {pid} successfully'
    except ProcessLookupError:
        return f'Error: process {pid} not found'
    except PermissionError:
        return f'Permission denied: cannot signal PID {pid}'
    except Exception as e:
        logger.error(f'Failed: {e}')
        return f'Error: {e}'

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
