#!/usr/bin/env python3

from typing import Optional, List
import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, contains_dangerous_chars

TOOL_CONFIG = {
    "name": "vc_repo_commit",
    "function": git_commit,
    "description": "提交Git仓库中的更改",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "仓库路径，默认为当前目录",
                "default": "."
            },
            "message": {
                "type": "string",
                "description": "提交信息"
            },
            "files": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "指定文件列表，可选"
            }
        },
        "required": ["message"]
    }
}
