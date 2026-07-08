#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from mcp_tools.cmd_safety_guard import validate_path_param

TOOL_CONFIG = {
    "name": "verify_nginx_config_syntax",
    "function": verify_nginx_config_syntax,
    "description": "校验Nginx配置文件语法正确性，返回错误信息、错误行号及修复建议",
    "version": "1.0.0",
    "author": "Nginx配置工具",
    "parameters": {
        "type": "object",
        "properties": {
            "config_path": {
                "type": "string",
                "description": "配置文件路径"
            },
            "config_content": {
                "type": "string",
                "description": "配置内容字符串"
            }
        },
        "oneOf": [
            {"required": ["config_path"]},
            {"required": ["config_content"]}
        ]
    },
    "examples": [
        {
            "name": "verify_nginx_config_syntax",
            "arguments": {
                "config_path": "/etc/nginx/nginx.conf"
            }
        },
        {
            "name": "verify_nginx_config_syntax",
            "arguments": {
                "config_content": "server { listen 80; server_name example.com; }"
            }
        }
    ]
}
