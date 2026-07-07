#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import glob
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation

TOOL_CONFIG = {
    "name": "modify_nginx_log_paths",
    "function": modify_nginx_log_paths,
    "description": "修改访问日志/错误日志的存储路径、文件名称",
    "version": "1.0.0",
    "author": "Nginx配置工具",
    "parameters": {
        "type": "object",
        "properties": {
            "cfg_filepath": {
                "type": "string",
                "description": "Nginx配置文件路径（可选，自动检测）"
            },
            "access_log_path": {
                "type": "string",
                "description": "新的访问日志路径（包含文件名）"
            },
            "error_log_path": {
                "type": "string",
                "description": "新的错误日志路径（包含文件名）"
            },
            "backup_original": {
                "type": "boolean",
                "description": "是否备份原始配置文件",
                "default": True
            }
        }
    },
    "examples": [
        {
            "name": "modify_nginx_log_paths",
            "arguments": {
                "access_log_path": "/var/log/nginx/new_access.log"
            }
        },
        {
            "name": "modify_nginx_log_paths",
            "arguments": {
                "error_log_path": "/var/log/nginx/new_error.log"
            }
        },
        {
            "name": "modify_nginx_log_paths",
            "arguments": {
                "access_log_path": "/var/log/nginx/custom_access.log",
                "error_log_path": "/var/log/nginx/custom_error.log"
            }
        }
    ]
}
