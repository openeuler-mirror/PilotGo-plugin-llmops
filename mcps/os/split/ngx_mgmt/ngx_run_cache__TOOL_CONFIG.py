#!/usr/bin/env python3

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

TOOL_CONFIG = {
    "name": "fetch_nginx_cache_stats",
    "description": "获取Nginx缓存统计信息，包括命中率、缓存大小、缓存配置等",
    "function": fetch_nginx_cache_stats,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
