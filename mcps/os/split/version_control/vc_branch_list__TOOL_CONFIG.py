#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param

TOOL_CONFIG = {
    "name": "show_branches",
    "function": show_branches,
    "description": "列出 Git 仓库的所有本地和远程分支信息",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "要查看分支的 Git 仓库目录（可选），如果不提供则使用当前目录"
            }
        },
        "required": []
    }
}
