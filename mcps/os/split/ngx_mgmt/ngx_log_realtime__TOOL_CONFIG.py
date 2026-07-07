#!/usr/bin/env python3

import subprocess
import platform
import os
import re
import logging
import time
import threading
import select
from datetime import datetime
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from .utils import (

TOOL_CONFIG = {
    "name": "tail_nginx_logs",
    "function": tail_nginx_logs,
    "description": "实时采集Nginx日志（类似tail -f），支持按日志类型/关键词过滤的MCP工具",
    "parameters": {
        "type": "object",
        "properties": {
            "log_type": {
                "type": "string",
                "description": "日志类型：access（访问日志）、error（错误日志）、both（两者都显示）",
                "enum": ["access", "error", "both"],
                "default": "access"
            },
            "filter_keyword": {
                "type": "string",
                "description": "关键词过滤（可选），只显示包含该关键词的日志行",
                "default": ""
            },
            "lines": {
                "type": "integer",
                "description": "显示初始行数",
                "minimum": 1,
                "maximum": 1000,
                "default": 50
            },
            "follow": {
                "type": "boolean",
                "description": "是否实时跟踪日志（类似tail -f）",
                "default": True
            },
            "duration": {
                "type": "integer",
                "description": "实时跟踪持续时间（秒）",
                "minimum": 10,
                "maximum": 3600,
                "default": 60
            }
        },
        "required": []
    }
}
