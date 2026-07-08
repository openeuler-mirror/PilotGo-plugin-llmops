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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_upstream_weight')


def reload_nginx_gracefully() -> bool:
    """
    平滑重载Nginx配置
    
    返回:
        bool: 重载是否成功
    """
    try:
        # 查找Nginx主进程PID
        nginx_pid = None
        for proc in psutil.process_iter(['pid', 'name', 'ppid']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                if proc.info['ppid'] == 1:  # 主进程的父进程是init
                    nginx_pid = proc.info['pid']
                    break
        
        if not nginx_pid:
            logger.error("未找到Nginx主进程")
            return False
        
        # 发送平滑重载信号
        os.kill(nginx_pid, 1)  # NOSONAR 
        logger.info(f"已向Nginx主进程({nginx_pid})发送平滑重载信号")
        
        # 等待重载完成
        time.sleep(2)
        
        # 检查Nginx是否正常运行
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'nginx' in proc.info['name'].lower():
                if proc.info['pid'] == nginx_pid:
                    logger.info("Nginx平滑重载成功")
                    return True
        
        logger.error("Nginx进程在重载后消失")
        return False
        
    except Exception as e:
        logger.error(f"平滑重载Nginx失败: {e}")
        return False
