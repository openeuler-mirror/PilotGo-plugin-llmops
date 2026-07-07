#!/usr/bin/env python3

import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_url_param, validate_path_param, validate_identifier_param


def git_clone(repo_url, target_dir=None, branch=None):
    """
    克隆Git仓库到指定目录

    参数:
    repo_url (str): Git仓库的URL地址
    target_dir (str, optional): 克隆到的目标目录，如果不提供则使用仓库名
    branch (str, optional): 要克隆的分支名，如果不提供或为空则默认为master

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - repo_url: 克隆的仓库URL
        - target_dir: 克隆到的目录
        - branch: 克隆的分支名
    """
    try:
        # 安全校验：验证 repo_url 参数
        is_valid, error_msg = validate_url_param(repo_url)
        if not is_valid:
            return {
                "status": "error",
                "message": f"仓库 URL 不合法：{error_msg}",
                "repo_url": repo_url,
                "target_dir": target_dir,
                "branch": branch
            }

        # 如果没有指定目标目录，则从 URL 中提取仓库名
        if not target_dir:
            # 先去除尾部斜杠，避免 split 后得到空字符串
            clean_url = repo_url.rstrip('/')
            repo_name = clean_url.split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            target_dir = repo_name

        # 安全校验：验证 target_dir 参数
        is_valid, error_msg = validate_path_param(target_dir, allow_absolute=True, allow_relative=True)
        if not is_valid:
            return {
                "status": "error",
                "message": f"目标目录不合法：{error_msg}",
                "repo_url": repo_url,
                "target_dir": target_dir,
                "branch": branch
            }

        # 安全校验：验证 branch 参数（如果提供了）
        if branch and branch.strip():  # 只有非空且非纯空白字符才验证
            is_valid, error_msg = validate_identifier_param(branch, allow_slash=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"分支名不合法：{error_msg}",
                    "repo_url": repo_url,
                    "target_dir": target_dir,
                    "branch": branch
                }

        # 设置分支：如果 branch 为空、None 或纯空白字符，则默认为 master
        if not branch or not branch.strip():
            branch = "master"

        # 检查目标目录是否已存在
        if os.path.exists(target_dir):
            return {
                "status": "error",
                "message": f"目标目录 '{target_dir}' 已存在",
                "repo_url": repo_url,
                "target_dir": target_dir,
                "branch": branch
            }

        # 执行git clone命令，使用--branch参数指定分支
        output = subprocess.run(["git", "clone", "--branch", branch, repo_url, target_dir], capture_output=True, text=True, check=True)

        return {
            "status": "success",
            "message": f"成功克隆仓库分支 '{branch}' 到 '{target_dir}'",
            "repo_url": repo_url,
            "target_dir": target_dir,
            "branch": branch,
            "output": output.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Git克隆失败: {e.stderr.strip()}",
            "repo_url": repo_url,
            "target_dir": target_dir,
            "branch": branch
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"克隆过程中发生错误: {e}",
            "repo_url": repo_url,
            "target_dir": target_dir,
            "branch": branch
        }
