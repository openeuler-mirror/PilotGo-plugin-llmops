#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, validate_identifier_param

TOOL_CONFIG = {
    "name": "vc_branch_create",
    "function": git_create_branch,
    "description": "创建 Git 分支",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Git 仓库目录（可选），如果不提供则使用当前目录"
            },
            "branch_name": {
                "type": "string",
                "description": "要创建的分支名称"
            },
            "checkout": {
                "type": "boolean",
                "description": "创建后是否切换到新分支，默认为 False"
            }
        },
        "required": ["branch_name"]
    }
}
