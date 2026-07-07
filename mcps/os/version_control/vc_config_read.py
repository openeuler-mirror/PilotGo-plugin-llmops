import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param

def git_get_user_info(scope="local", directory=None):
    """
    获取Git用户信息（name和email）

    参数:
    scope (str, optional): 配置范围，可选值为 "local"、"global" 或 "system"，默认为 "local"
    directory (str, optional): 要查看配置的Git仓库目录，仅对local范围有效，如果不提供则使用当前目录

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - scope: 配置范围
        - directory: 查看配置的目录（仅对local范围有效）
        - user_info: 用户信息字典，包含name和email字段
        - output: Git config命令的完整输出
    """
    try:
        # 验证scope参数
        valid_scopes = ["local", "global", "system"]
        if scope not in valid_scopes:
            return {
                "status": "error",
                "message": f"无效的scope参数，必须是 {', '.join(valid_scopes)} 之一",
                "scope": scope,
                "directory": directory,
                "user_info": {},
                "output": ""
            }

        # 如果是 local 范围，检查目录是否存在和是否是 Git 仓库
        if scope == "local":
            target_dir = directory if directory else os.getcwd()

            # 安全校验：验证目录路径（如果提供了 directory 参数）
            if directory:
                is_valid, error_msg = validate_path_param(target_dir, allow_absolute=True, allow_relative=True)
                if not is_valid:
                    return {
                        "status": "error",
                        "message": f"目录不合法：{error_msg}",
                        "scope": scope,
                        "directory": target_dir,
                        "user_info": {},
                        "output": ""
                    }

            if not os.path.exists(target_dir):
                return {
                    "status": "error",
                    "message": f"目录 '{target_dir}' 不存在",
                    "scope": scope,
                    "directory": target_dir,
                    "user_info": {},
                    "output": ""
                }

            # 检查目录是否是Git仓库
            git_dir = os.path.join(target_dir, ".git")
            if not os.path.exists(git_dir):
                return {
                    "status": "error",
                    "message": f"目录 '{target_dir}' 不是Git仓库",
                    "scope": scope,
                    "directory": target_dir,
                    "user_info": {},
                    "output": ""
                }

        # 执行git config命令获取user.name
        name_cmd = ["git", "config", f"--{scope}", "user.name"]
        name_result = subprocess.run(
            name_cmd,
            cwd=directory if directory and scope == "local" else None,
            capture_output=True,
            text=True
        )

        # 执行git config命令获取user.email
        email_cmd = ["git", "config", f"--{scope}", "user.email"]
        email_result = subprocess.run(
            email_cmd,
            cwd=directory if directory and scope == "local" else None,
            capture_output=True,
            text=True
        )

        # 提取用户信息
        user_name = name_result.stdout.strip() if name_result.returncode == 0 else None
        user_email = email_result.stdout.strip() if email_result.returncode == 0 else None

        # 构建用户信息字典
        user_info = {}
        if user_name:
            user_info["name"] = user_name
        if user_email:
            user_info["email"] = user_email

        # 验证是否获取到用户信息
        if not user_info:
            return {
                "status": "error",
                "message": f"在 {scope} 范围内未找到Git用户配置信息",
                "scope": scope,
                "directory": directory,
                "user_info": {},
                "output": ""
            }

        return {
            "status": "success",
            "message": f"成功获取Git {scope} 用户信息",
            "scope": scope,
            "directory": directory,
            "user_info": user_info,
            "output": f"user.name={user_name if user_name else ''}\nuser.email={user_email if user_email else ''}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"获取Git用户信息过程中发生错误: {e}",
            "scope": scope,
            "directory": directory,
            "user_info": {},
            "output": ""
        }

# 工具配置
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
