import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, validate_identifier_param


def git_push(directory=None, remote=None, branch=None, force=False, tags=False):
    """
    推送 Git 仓库中的更改到远程仓库

    参数:
    directory (str, optional): Git 仓库目录，如果不提供则使用当前目录
    remote (str, optional): 远程仓库名称，默认为"origin"
    branch (str, optional): 分支名称，默认为当前分支
    force (bool, optional): 是否强制推送，默认为 False
    tags (bool, optional): 是否推送标签，默认为 False

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: Git 仓库目录
        - remote: 远程仓库名称
        - branch: 分支名称
        - force: 是否强制推送
        - tags: 是否推送标签
    """
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
                    "remote": remote,
                    "branch": branch,
                    "force": force,
                    "tags": tags
                }
            # 检查目录是否存在
            if not os.path.exists(target_dir):
                return {
                    "status": "error",
                    "message": f"目录 '{target_dir}' 不存在",
                    "directory": target_dir,
                    "remote": remote,
                    "branch": branch,
                    "force": force,
                    "tags": tags
                }
        else:
            target_dir = os.getcwd()

        # 设置默认远程仓库
        if not remote:
            remote = "origin"

        # 安全校验：验证远程仓库名称
        is_valid, error_msg = validate_identifier_param(remote)
        if not is_valid:
            return {
                "status": "error",
                "message": f"远程仓库名称不合法：{error_msg}",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }

        # 安全校验：验证分支名称（如果提供）
        if branch:
            is_valid, error_msg = validate_identifier_param(branch, allow_slash=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"分支名称不合法：{error_msg}",
                    "directory": target_dir,
                    "remote": remote,
                    "branch": branch,
                    "force": force,
                    "tags": tags
                }

        # 检查目录是否是 Git仓库
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不是Git仓库",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }

        # 检查远程仓库是否存在
        remote_check = subprocess.run(["git", "-C", target_dir, "remote", "get-url", remote], capture_output=True, text=True)

        if remote_check.returncode != 0:
            return {
                "status": "error",
                "message": f"远程仓库 '{remote}' 不存在",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }

        # 如果没有指定分支，获取当前分支
        if not branch:
            branch_result = subprocess.run(["git", "-C", target_dir, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
            branch = branch_result.stdout.strip()

        # 构建 git push 命令
        cmd = ["git", "-C", target_dir, "push"]

        if force:
            cmd.append("--force")

        if tags:
            cmd.append("--tags")

        cmd.append(remote)
        cmd.append(branch)

        # 执行命令
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # 构建返回结果
        action = f"推送{'' if not tags else '标签和'}分支 '{branch}' 到远程仓库 '{remote}'"
        if force:
            action = "强制" + action

        return {
            "status": "success",
            "message": f"成功{action}",
            "directory": target_dir,
            "remote": remote,
            "branch": branch,
            "force": force,
            "tags": tags,
            "output": output.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        # 检查常见错误类型
        if "could not read Username" in e.stderr or "authentication failed" in e.stderr:
            return {
                "status": "error",
                "message": "认证失败，请检查 Git 凭证配置",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }
        elif "src refspec" in e.stderr:
            return {
                "status": "error",
                "message": f"分支 '{branch}' 不存在",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }
        elif "rejected" in e.stderr:
            return {
                "status": "error",
                "message": "推送被拒绝，可能需要先拉取最新更改或使用强制推送",
                "directory": target_dir,
                "remote": remote,
                "branch": branch,
                "force": force,
                "tags": tags
            }
        return {
            "status": "error",
            "message": f"Git 推送失败: {e.stderr.strip()}",
            "directory": target_dir,
            "remote": remote,
            "branch": branch,
            "force": force,
            "tags": tags
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"推送过程中发生错误: {e}",
            "directory": target_dir,
            "remote": remote,
            "branch": branch,
            "force": force,
            "tags": tags
        }


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
