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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


def fetch_nginx_config_content():
    """获取Nginx配置文件内容"""
    try:
        # 使用 nginx -T 命令获取完整配置
        output = subprocess.run(
            ['nginx', '-T'], 
            capture_output=True, 
            text=True, 
            stderr=subprocess.STDOUT,
            timeout=10
        )
        
        if output.returncode in [0, 1]:
            return output.stdout
        else:
            logger.error(f'nginx -T 命令执行失败: {output.stderr}')
            return ""
            
    except subprocess.TimeoutExpired:
        logger.error('nginx -T 命令执行超时')
        return ""
    except FileNotFoundError:
        logger.error('nginx 命令未找到')
        return ""
    except Exception as e:
        logger.error(f'获取Nginx配置失败: {e}')
        return ""
