#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_include')


def fetch_nginx_config_include() -> Dict:
    """
    获取主配置中include的所有子配置路径、加载顺序、生效状态

    返回:
        dict: 包含include状态信息的字典
    """
    output = fetch_config_include_status()

    # 如果没有错误，添加展平的include列表
    if 'include_tree' in output:
        output['flat_includes'] = flatten_include_tree(output['include_tree'])

    return output
