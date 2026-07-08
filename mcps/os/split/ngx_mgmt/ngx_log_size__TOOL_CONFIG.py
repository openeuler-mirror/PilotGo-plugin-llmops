#!/usr/bin/env python3

import os
import re
import subprocess
import logging
import shutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, check_nginx_installation
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param

TOOL_CONFIG = {
    'name': 'fetch_nginx_log_size',
    'description': '获取Nginx日志文件的大小统计信息，包括总大小、按类型和目录分类的大小',
    'category': 'Nginx',
    'function': fetch_nginx_log_size,
    'output_format': 'json'
}
