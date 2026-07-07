#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, contains_dangerous_chars

TOOL_CONFIG = {
    "name": "vc_diff_staged",
    "function": git_diff_staged,
    "description": "查看Git仓库中已暂存的变更",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "要查看变更的Git仓库目录（可选），如果不提供则使用当前目录"
            },
            "files": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "指定要查看变更的文件列表（可选），如果不提供则查看所有文件的变更"
            }
        },
        "required": []
    }
}
