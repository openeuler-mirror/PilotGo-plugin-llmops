#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param

TOOL_CONFIG = {
    "name": "vc_repo_state",
    "function": git_status,
    "description": "查看 Git 仓库的状态信息",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "要查看状态的 Git 仓库目录（可选），如果不提供则使用当前目录"
            }
        },
        "required": []
    }
}
