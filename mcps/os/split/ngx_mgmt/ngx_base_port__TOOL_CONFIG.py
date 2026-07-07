#!/usr/bin/env python3

import glob
import glob
import logging
import os
import re
import socket
import subprocess

from .utils import check_nginx_installation, get_nginx_config_info

TOOL_CONFIG = {
    "name": "fetch_nginx_base_port",
    "function": fetch_nginx_base_port,
    "description": "获取Nginx监听的所有TCP/UDP端口、绑定IP以及端口对应的站点配置的MCP工具",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
