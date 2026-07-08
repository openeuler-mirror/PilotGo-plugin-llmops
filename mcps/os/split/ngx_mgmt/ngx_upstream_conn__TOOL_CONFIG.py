#!/usr/bin/env python3

import os
import re
import json
import logging
import subprocess
import socket
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import psutil

TOOL_CONFIG = {
    'name': 'fetch_nginx_upstream_connection',
    'description': '获取Nginx配置文件中定义的所有上游服务的连接数信息，包括总连接数、活跃连接数、最大连接数等',
    'category': 'Nginx',
    'function': fetch_nginx_upstream_connection,
    'output_format': 'json'
}
