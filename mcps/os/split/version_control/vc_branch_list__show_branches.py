#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param


def show_branches(directory=None):
    """
    列出 Git 仓库的所有本地和远程分支

    参数:
    directory (str, optional): 要查看分支的 Git 仓库目录，如果不提供则使用当前目录

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: 查看分支的目录
        - branches: 分支列表
        - current_branch: 当前所在分支
        - output: Git branch 命令的完整输出
        - is_repo: 是否是 Git 仓库
    """
    try:
        # 确定目标目录
        target_dir = directory if directory else os.getcwd()

        # 安全校验：验证目录路径
        if directory:
            is_valid, error_msg = validate_path_param(target_dir, allow_absolute=True, allow_relative=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"仓库目录不合法：{error_msg}",
                    "directory": target_dir,
                    "branches": [],
                    "current_branch": "",
                    "output": "",
                    "is_repo": False
                }

        # 检查目录是否存在
        if not os.path.exists(target_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不存在",
                "directory": target_dir,
                "branches": [],
                "current_branch": "",
                "output": "",
                "is_repo": False
            }

        # 检查目录是否是 Git 仓库
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不是Git仓库",
                "directory": target_dir,
                "branches": [],
                "current_branch": "",
                "output": "",
                "is_repo": False
            }

        # 执行 git branch -a 命令，获取所有分支（本地和远程）
        output = subprocess.run(
            ["git", "branch", "-a"],
            cwd=target_dir,  # 在指定目录执行命令
            capture_output=True,
            text=True,
            check=True
        )

        # 解析分支信息
        branch_lines = output.stdout.strip().split("\n")
        branches = []
        current_branch = ""

        for line in branch_lines:
            if line.strip():
                # 检查是否是当前分支（以*开头）
                if line.startswith("*"):
                    current_branch = line[1:].strip()
                    branches.append({
                        "name": current_branch,
                        "type": "local",
                        "is_current": True
                    })
                else:
                    branch_name = line.strip()
                    # 区分本地分支和远程分支
                    if branch_name.startswith("remotes/"):
                        branches.append({
                            "name": branch_name,
                            "type": "remote",
                            "is_current": False
                        })
                    else:
                        branches.append({
                            "name": branch_name,
                            "type": "local",
                            "is_current": False
                        })

        return {
            "status": "success",
            "message": f"成功获取仓库所有分支，共 {len(branches)} 个分支",
            "directory": target_dir,
            "branches": branches,
            "current_branch": current_branch,
            "output": output.stdout.strip(),
            "is_repo": True
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"获取分支列表失败: {e.stderr.strip()}",
            "directory": target_dir,
            "branches": [],
            "current_branch": "",
            "output": "",
            "is_repo": True  # 已经确认是 Git 仓库，但命令执行失败
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取分支列表过程中发生错误: {e}",
            "directory": target_dir,
            "branches": [],
            "current_branch": "",
            "output": "",
            "is_repo": False
        }
