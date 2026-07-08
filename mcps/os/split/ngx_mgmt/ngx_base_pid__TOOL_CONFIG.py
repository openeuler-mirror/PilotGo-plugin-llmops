#!/usr/bin/env python3

from datetime import datetime
import logging
import os
import re
import subprocess

import psutil
import pwd, grp

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

TOOL_CONFIG = {
    "name": "fetch_nginx_base_pid",
    "function": fetch_nginx_base_pid,
    "description": "获取Nginx进程详细信息，包括PID、用户/组、资源使用和进程树关系",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
