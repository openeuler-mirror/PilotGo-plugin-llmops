#!/usr/bin/env python3

from typing import Dict, List, Tuple, Any, Optional
import logging
import os
import re
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

TOOL_CONFIG = {
    "name": "fetch_global_config",
    "description": "聚合获取所有全局配置项（如worker_processes、worker_connections）",
    "function": fetch_global_config,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
