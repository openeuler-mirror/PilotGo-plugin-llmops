#!/usr/bin/env python3

import json
import os
import re
import subprocess
import logging
import shutil
from datetime import datetime
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

import psutil

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

TOOL_CONFIG = {
    'name': 'set_upstream_server_weight',
    'description': '设置指定上游服务器的权重，支持平滑生效',
    'category': 'Nginx',
    'function': set_upstream_server_weight,
    'input_schema': {
        'type': 'object',
        'properties': {
            'upstream_name': {
                'type': 'string',
                'description': 'upstream服务组名称'
            },
            'server_address': {
                'type': 'string',
                'description': '服务器地址（格式：ip:port 或 domain:port）'
            },
            'weight': {
                'type': 'integer',
                'description': '权重值（1-1000）',
                'minimum': 1,
                'maximum': 1000
            },
            'graceful_reload': {
                'type': 'boolean',
                'description': '是否平滑重载Nginx',
                'default': True
            }
        },
        'required': ['upstream_name', 'server_address', 'weight']
    },
    'examples': [
        {
            'description': '设置backend服务组中192.168.1.100:8080服务器的权重为50',
            'input': {
                'upstream_name': 'backend',
                'server_address': '192.168.1.100:8080',  # NOSONAR
                'weight': 50,
                'graceful_reload': True
            }
        },
        {
            'description': '设置api服务组中api.example.com:443服务器的权重为100，不自动重载',
            'input': {
                'upstream_name': 'api',
                'server_address': 'api.example.com:443',
                'weight': 100,
                'graceful_reload': False
            }
        }
    ]
}
