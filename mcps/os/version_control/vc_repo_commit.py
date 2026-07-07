from typing import Optional, List
import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, contains_dangerous_chars

def git_commit(repo_path: str = ".", message: str = "", files: Optional[List[str]] = None):
    """
    提交 Git 仓库中的更改

    参数:
    repo_path (str, optional): 仓库路径，默认为当前目录
    message (str): 提交信息
    files (List[str], optional): 指定文件列表

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - repo_path: 仓库路径
        - commit_message: 提交信息
    """
    try:
        # 安全校验：验证仓库路径参数
        is_valid, error_msg = validate_path_param(repo_path, allow_absolute=True, allow_relative=True)
        if not is_valid:
            return {
                "status": "error",
                "message": f"仓库路径不合法：{error_msg}",
                "repo_path": repo_path,
                "commit_message": message
            }

        # 安全校验：验证提交消息
        # 注意：Git 提交消息可以包含特殊字符（如#用于引用 issue），只要用引号包裹就是安全的
        # 只需要检查明显的命令注入特征
        if message:
            harmful_patterns = [';', '|', '&', '$', '`']
            if any(pattern in message for pattern in harmful_patterns):
                return {
                    "status": "error",
                    "message": "提交消息包含非法字符",
                    "repo_path": repo_path,
                    "commit_message": message
                }

        # 检查目录是否存在
        if not os.path.exists(repo_path):
            return {
                "status": "error",
                "message": f"目录 '{repo_path}' 不存在",
                "repo_path": repo_path,
                "commit_message": message
            }

        # 检查目录是否是Git仓库
        git_dir = os.path.join(repo_path, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{repo_path}' 不是Git仓库",
                "repo_path": repo_path,
                "commit_message": message
            }

        # 检查是否提供了提交消息
        if not message:
            return {
                "status": "error",
                "message": "必须提供提交消息",
                "repo_path": repo_path,
                "commit_message": message
            }

        # 构建git commit命令
        cmd = ["git", "-C", repo_path, "commit", "-m", message]

        # 如果指定了文件列表，则添加文件
        if files:
            # 先执行git add添加指定文件
            add_cmd = ["git", "-C", repo_path, "add"] + files
            subprocess.run(
                add_cmd,
                capture_output=True,
                text=True,
                check=True
            )

        # 执行git commit命令
        output = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return {
            "status": "success",
            "message": "提交成功",
            "repo_path": repo_path,
            "commit_message": message,
            "output": output.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        # 检查错误类型
        if "nothing to commit" in e.stderr:
            return {
                "status": "error",
                "message": "没有需要提交的更改",
                "repo_path": repo_path,
                "commit_message": message
            }
        elif "no changes added to commit" in e.stderr:
            return {
                "status": "error",
                "message": "没有添加到提交的更改，请先使用git add添加文件",
                "repo_path": repo_path,
                "commit_message": message
            }
        return {
            "status": "error",
            "message": f"Git提交失败: {e.stderr.strip()}",
            "repo_path": repo_path,
            "commit_message": message
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"提交过程中发生错误: {e}",
            "repo_path": repo_path,
            "commit_message": message
        }

# 工具配置
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
