#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

TOOL_CONFIG = {
    "name": "fetch_nginx_config_include",
    "description": "获取主配置中include的所有子配置路径、加载顺序、生效状态",
    "function": fetch_nginx_config_include,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
