#!/usr/bin/env python3

import subprocess
import psutil
import os
import time
import logging
from datetime import datetime
import signal

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

TOOL_CONFIG = {
    "name": "perform_nginx_stop",
    "function": perform_nginx_stop,
    "description": "安全停止Nginx进程，支持平滑停止（等待连接释放）、立即停止和强制停止",
    "parameters": {
        "type": "object",
        "properties": {
            "stop_type": {
                "type": "string",
                "enum": ["graceful", "immediate", "force"],
                "description": "停止类型：graceful(平滑停止)、immediate(立即停止)、force(强制停止)",
                "default": "graceful"
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒），默认300秒",
                "default": 300
            },
            "wait_connections": {
                "type": "boolean",
                "description": "是否等待连接释放，默认True",
                "default": True
            }
        },
        "required": []
    }
}
