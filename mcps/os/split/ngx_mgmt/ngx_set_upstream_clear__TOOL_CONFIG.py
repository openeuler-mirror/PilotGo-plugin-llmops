#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

TOOL_CONFIG = {
    "name": "clear_upstream_fail_stats",
    "function": clear_upstream_fail_stats,
    "description": "清空上游服务器的失败请求统计、重置熔断状态、恢复故障服务器",
    "version": "1.0.0",
    "parameters": {
        "type": "object",
        "properties": {
            "upstream_name": {
                "type": "string",
                "description": "上游服务器名称",
                "default": ""
            },
            "operation_type": {
                "type": "string",
                "enum": ["reset_circuit_breaker", "clear_fail_stats", "restore_server"],
                "description": "操作类型",
                "default": "reset_circuit_breaker"
            },
            "server_address": {
                "type": "string",
                "description": "特定服务器地址（可选，用于恢复单个服务器）",
                "default": ""
            }
        },
        "required": ["upstream_name"]
    },
    "examples": [
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "backend",
                "operation_type": "reset_circuit_breaker"
            }
        },
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "api_servers",
                "operation_type": "clear_fail_stats"
            }
        },
        {
            "name": "clear_upstream_fail_stats",
            "parameters": {
                "upstream_name": "backend",
                "operation_type": "restore_server",
                "server_address": "192.168.1.100:8080"  # NOSONAR
            }
        }
    ]
}
