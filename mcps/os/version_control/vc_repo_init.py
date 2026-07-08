import os
import subprocess

from mcp_tools.cmd_safety_guard import validate_path_param


def git_init(directory=None, bare=False):
    """
    初始化 Git 仓库

    参数:
    directory (str, optional): 要初始化仓库的目录，如果不提供则使用当前目录
    bare (bool, optional): 是否创建裸仓库，默认为 False

    返回:
    dict: 包含操作结果的字典
        - status: 操作状态，"success"或"error"
        - message: 操作结果的详细信息
        - directory: 初始化仓库的目录
        - bare: 是否为裸仓库
    """
    # 初始化变量以避免作用域问题
    target_dir = None

    try:
        # 确定目标目录
        if directory:
            target_dir = directory
            # 安全校验：验证目录路径
            is_valid, error_msg = validate_path_param(target_dir, allow_absolute=True, allow_relative=True)
            if not is_valid:
                return {
                    "status": "error",
                    "message": f"目录不合法：{error_msg}",
                    "directory": target_dir,
                    "bare": bare
                }
            # 检查目录是否存在，如果不存在则创建
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
        else:
            target_dir = os.getcwd()

        # 检查目录是否已经是 Git 仓库
        git_dir = os.path.join(target_dir, ".git")
        if os.path.exists(git_dir):
            return {
                "status": "error",
                "message": f"目录 '{target_dir}' 已经是一个Git仓库",
                "directory": target_dir,
                "bare": bare
            }

        # 构建 git init 命令
        cmd = ["git", "init"]
        if bare:
            cmd.append("--bare")

        # 执行 git init 命令，在指定目录下执行
        output = subprocess.run(
            cmd,
            cwd=target_dir,  # 在指定目录执行命令
            capture_output=True,
            text=True,
            check=True
        )

        # 构建返回结果
        repo_type = "裸仓库" if bare else "标准仓库"
        return {
            "status": "success",
            "message": f"成功在 '{target_dir}' 初始化{repo_type}",
            "directory": target_dir,
            "bare": bare,
            "output": output.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Git初始化失败：{e.stderr.strip()}",
            "directory": target_dir if target_dir is not None else (directory if directory else os.getcwd()),
            "bare": bare
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"初始化过程中发生错误: {e}",
            "directory": target_dir if target_dir is not None else (directory if directory else os.getcwd()),
            "bare": bare
        }


TOOL_CONFIG = {
    "name": "vc_repo_init",
    "function": git_init,
    "description": "初始化 Git 仓库",
    "parameters": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "要初始化仓库的目录（可选），如果不提供则使用当前目录"
            },
            "bare": {
                "type": "boolean",
                "description": "是否创建裸仓库，默认为 False"
            }
        },
        "required": []
    }
}
