import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param


def git_status(directory=None):
    """
    查看 Git 仓库的状态

    参数:
    directory (str, optional): 要查看状态的 Git 仓库目录，如果不提供则使用当前目录

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: 查看状态的目录
        - output: Git 状态的完整输出
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
                    "output": "",
                    "is_repo": False
                }

        # 检查目录是否存在
        if not os.path.exists(target_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不存在",
                "directory": target_dir,
                "output": "",
                "is_repo": False
            }

        # 检查目录是否是 Git仓库
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不是Git仓库",
                "directory": target_dir,
                "output": "",
                "is_repo": False
            }

        # 执行 git status 命令
        output = subprocess.run(
            ["git", "status"],
            cwd=target_dir,  # 在指定目录执行命令
            capture_output=True,
            text=True,
            check=True
        )

        # 解析状态信息
        status_lines = output.stdout.strip().split("\n")
        branch_info = status_lines[0] if status_lines else "未知分支"

        return {
            "status": "success",
            "message": f"成功获取仓库状态 - {branch_info}",
            "directory": target_dir,
            "output": output.stdout.strip(),
            "is_repo": True
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"获取Git状态失败：{e.stderr.strip()}",
            "directory": target_dir,
            "output": "",
            "is_repo": True  # 已经确认是 Git仓库，但命令执行失败
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取状态过程中发生错误: {e}",
            "directory": target_dir,
            "output": "",
            "is_repo": False
        }


TOOL_CONFIG = {
    "name": "vc_repo_state",
    "function": git_status,
    "description": "查看 Git 仓库的状态信息",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "要查看状态的 Git 仓库目录（可选），如果不提供则使用当前目录"
            }
        },
        "required": []
    }
}
