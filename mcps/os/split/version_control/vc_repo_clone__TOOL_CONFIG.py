#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_url_param, validate_path_param, validate_identifier_param

TOOL_CONFIG = {
    "name": "vc_repo_clone",
    "function": git_clone,
    "description": "克隆Git仓库到指定目录",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "Git仓库的URL地址，例如：https://github.com/username/repo.git"
            },
            "target_dir": {
                "type": "string",
                "description": "克隆到的目标目录（可选），如果不提供则使用仓库名"
            },
            "branch": {
                "type": "string",
                "description": "要克隆的分支名（可选），如果不提供或为空则默认为master"
            }
        },
        "required": ["repo_url"]
    }
}
