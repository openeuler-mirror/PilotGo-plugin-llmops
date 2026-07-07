#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, validate_identifier_param

TOOL_CONFIG = {
    "name": "vc_repo_push",
    "function": git_push,
    "description": "推送 Git 仓库中的更改到远程仓库",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Git 仓库目录（可选），如果不提供则使用当前目录"
            },
            "remote": {
                "type": "string",
                "description": "远程仓库名称（可选），默认为\"origin\""
            },
            "branch": {
                "type": "string",
                "description": "分支名称（可选），默认为当前分支"
            },
            "force": {
                "type": "boolean",
                "description": "是否强制推送，默认为 False"
            },
            "tags": {
                "type": "boolean",
                "description": "是否推送标签，默认为 False"
            }
        },
        "required": []
    }
}
