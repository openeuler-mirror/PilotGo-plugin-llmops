#!/usr/bin/env python3

from datetime import datetime
from typing import Dict, Optional, List
import json
import logging
import os
import re
import subprocess
import time

import psutil
import requests

TOOL_CONFIG = {
    "name": "fetch_nginx_runtime_request",
    "function": fetch_nginx_runtime_request,
    "description": "获取Nginx运行时请求统计，包括总请求数、QPS、TP99/TP95响应时间、成功/失败请求数等",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
