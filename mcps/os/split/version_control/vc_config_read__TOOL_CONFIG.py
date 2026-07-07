#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param

TOOL_CONFIG = {
    "name": "git_get_user_info",
    "function": git_get_user_info,
    "description": "获取当前配置的Git用户信息（name和email）",
    "parameters": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "description": "配置范围，可选值为 \"local\"、\"global\" 或 \"system\"，默认为 \"local\"",
                "default": "local"
            },
            "directory": {
                "type": "string",
                "description": "要查看配置的Git仓库目录（可选），仅对local范围有效，如果不提供则使用当前目录"
            }
        },
        "required": []
    }
}
