#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, validate_identifier_param


def git_create_branch(directory=None, branch_name=None, checkout=False):
    """
    创建 Git 分支

    参数:
    directory (str, optional): Git 仓库目录，如果不提供则使用当前目录
    branch_name (str): 要创建的分支名称
    checkout (bool, optional): 创建后是否切换到新分支，默认为 False

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: Git 仓库目录
        - branch_name: 新分支名称
        - checkout: 是否切换到新分支
    """
    target_dir = None  # 初始化 target_dir 变量，确保在异常处理中可用
    try:
        # 确定目标目录
        if directory:
            target_dir = directory
            # 安全校验：验证目录路径
            is_valid, error_msg = validate_path_param(target_dir, allow_absolute=True, allow_relative=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"仓库目录不合法：{error_msg}",
                    "directory": target_dir,
                    "branch_name": branch_name,
                    "checkout": checkout
                }
            # 检查目录是否存在
            if not os.path.exists(target_dir):
                return {
                    "status": "error",
                    "message": f"目录 '{target_dir}' 不存在",
                    "directory": target_dir,
                    "branch_name": branch_name,
                    "checkout": checkout
                }
        else:
            target_dir = os.getcwd()

        # 安全校验：验证分支名称（只有非空且非纯空白字符才验证）
        if branch_name and branch_name.strip():
            is_valid, error_msg = validate_identifier_param(branch_name, allow_slash=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"分支名称不合法：{error_msg}",
                    "directory": target_dir,
                    "branch_name": branch_name,
                    "checkout": checkout
                }

        # 检查目录是否是 Git仓库
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不是Git仓库",
                "directory": target_dir,
                "branch_name": branch_name,
                "checkout": checkout
            }

        # 检查是否提供了分支名称
        if not branch_name:
            return {
                "status": "error",
                "message": "必须提供分支名称",
                "directory": target_dir,
                "branch_name": branch_name,
                "checkout": checkout
            }

        # 检查分支是否已存在
        branch_check = subprocess.run(["git", "-C", target_dir, "branch", "--list", branch_name], capture_output=True, text=True)

        if branch_check.stdout.strip():
            return {
                "status": "error",
                "message": f"分支 '{branch_name}' 已存在",
                "directory": target_dir,
                "branch_name": branch_name,
                "checkout": checkout
            }

        # 构建 git branch 命令
        if checkout:
            # 创建并切换到新分支
            cmd = ["git", "-C", target_dir, "checkout", "-b", branch_name]
        else:
            # 只创建分支
            cmd = ["git", "-C", target_dir, "branch", branch_name]

        # 执行命令
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # 构建返回结果
        action = f"创建并切换到分支 '{branch_name}'" if checkout else f"创建分支 '{branch_name}'"
        return {
            "status": "success",
            "message": f"成功{action}",
            "directory": target_dir,
            "branch_name": branch_name,
            "checkout": checkout,
            "output": output.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Git分支操作失败：{e.stderr.strip()}",
            "directory": target_dir if target_dir is not None else directory if directory is not None else os.getcwd(),
            "branch_name": branch_name,
            "checkout": checkout
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"分支操作过程中发生错误: {e}",
            "directory": target_dir if target_dir is not None else directory if directory is not None else os.getcwd(),
            "branch_name": branch_name,
            "checkout": checkout
        }
