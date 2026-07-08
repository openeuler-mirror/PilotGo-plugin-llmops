import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param, contains_dangerous_chars


def git_diff_staged(directory=None, files=None):
    """
    查看 Git 仓库中已暂存的变更

    参数:
    directory (str, optional): 要查看变更的 Git 仓库目录，如果不提供则使用当前目录
    files (list, optional): 指定要查看变更的文件列表，如果不提供则查看所有文件的变更

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: 查看变更的目录
        - files: 查看变更的文件列表（如果提供）
        - diff: 已暂存变更的详细内容
        - output: Git diff 命令的完整输出
        - has_changes: 是否存在已暂存的变更
    """
    # 初始化变量以避免作用域问题
    target_dir = None

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
                    "files": files,
                    "diff": "",
                    "output": "",
                    "has_changes": False
                }

        # 安全校验：验证文件列表中的每个文件名
        if files:
            for file in files:
                if contains_dangerous_chars(file, allow_space=False):
                    return {
                        "status": "error",
                        "message": f"文件名 '{file}' 包含非法字符",
                        "directory": target_dir,
                        "files": files,
                        "diff": "",
                        "output": "",
                        "has_changes": False
                    }

        # 检查目录是否存在
        if not os.path.exists(target_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不存在",
                "directory": target_dir,
                "files": files,
                "diff": "",
                "output": "",
                "has_changes": False
            }

        # 检查目录是否是Git仓库
        git_dir = os.path.join(target_dir, ".git")
        if not os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 不是Git仓库",
                "directory": target_dir,
                "files": files,
                "diff": "",
                "output": "",
                "has_changes": False
            }

        # 构建git diff --staged命令
        cmd = ["git", "diff", "--staged"]

        # 如果指定了文件列表，添加文件参数
        if files:
            cmd.extend(files)

        # 执行git diff --staged命令
        output = subprocess.run(
            cmd,
            cwd=target_dir,  # 在指定目录执行命令
            capture_output=True,
            text=True,
            check=True
        )

        # 检查是否有已暂存的变更
        has_changes = len(output.stdout.strip()) > 0

        return {
            "status": "success",
            "message": "成功获取已暂存的变更" if has_changes else "没有已暂存的变更",
            "directory": target_dir,
            "files": files,
            "diff": output.stdout.strip(),
            "output": output.stdout.strip(),
            "has_changes": has_changes
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"获取已暂存变更失败: {e.stderr.strip() if e.stderr else 'Unknown error'}",
            "directory": target_dir if target_dir is not None else (directory if directory else os.getcwd()),
            "files": files,
            "diff": "",
            "output": "",
            "has_changes": False
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"获取已暂存变更过程中发生错误: {e}",
            "directory": target_dir if target_dir is not None else (directory if directory else os.getcwd()),
            "files": files,
            "diff": "",
            "output": "",
            "has_changes": False
        }


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
