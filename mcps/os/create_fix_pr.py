#!/usr/bin/env python3
"""
生成修复PR：修复上游仓库中8个有错误的文件
从本地 split/ 目录复制正确文件到 fork 仓库，然后创建 PR
"""

import os
import json
import urllib.request
import base64

# 配置
UPSTREAM_OWNER = "openeuler"
REPO = "PilotGo-plugin-llmops"
FORK_OWNER = "songyuqin0686"
FORK_REPO_PATH = "/home/syq/桌面/mcp_tools_part1/syq/PilotGo-plugin-llmops"
TOKEN = "-LPAzJ5mp28wujLjyPd_TicY"
SPLIT_DIR = "/home/syq/桌面/mcp_tools_part1/split"

# 需要修复的文件列表（上游路径 -> 本地正确文件路径）
FILES_TO_FIX = {
    "mcps/os/split_files__extract_imports_block.py": os.path.join(SPLIT_DIR, "split_files__extract_imports_block.py"),
    "mcps/os/split_files__extract_tool_config_block.py": os.path.join(SPLIT_DIR, "split_files__extract_tool_config_block.py"),
    "mcps/os/split_files__build_file_content.py": os.path.join(SPLIT_DIR, "split_files__build_file_content.py"),
    "mcps/os/split_files__generate_init_files.py": os.path.join(SPLIT_DIR, "split_files__generate_init_files.py"),
    "mcps/os/split_files__get_func_source.py": os.path.join(SPLIT_DIR, "split_files__get_func_source.py"),
    "mcps/os/split_files__main.py": os.path.join(SPLIT_DIR, "split_files__main.py"),
    "mcps/os/split_files__split_file.py": os.path.join(SPLIT_DIR, "split_files__split_file.py"),
    "mcps/os/split_files__extract_logging_block.py": os.path.join(SPLIT_DIR, "split_files__extract_logging_block.py"),
}


def run_git(cmd, cwd=FORK_REPO_PATH):
    """执行 git 命令"""
    import subprocess
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  git 错误: {result.stderr.strip()}")
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()


def main():
    print("=== 生成修复PR ===")
    print(f"需要修复 {len(FILES_TO_FIX)} 个文件\n")

    # 1. 同步 fork 仓库
    print("1. 同步 fork 仓库...")
    run_git("git fetch upstream")
    run_git("git checkout master")
    run_git("git reset --hard upstream/master")
    run_git("git push --force origin master")

    # 2. 复制正确文件
    print("\n2. 复制正确文件...")
    for repo_path, local_path in FILES_TO_FIX.items():
        target = os.path.join(FORK_REPO_PATH, repo_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        # 读取本地正确文件
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 写入 fork 仓库
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  已复制: {repo_path}")

    # 3. 提交
    print("\n3. 提交修改...")
    run_git("git add -A")
    run_git('git commit -m "fix: remove orphaned code fragments from split files"')

    # 4. 推送
    print("\n4. 推送到 fork...")
    run_git("git push --force origin master")

    # 5. 创建 PR
    print("\n5. 创建修复 PR...")
    url = f"https://api.atomgit.com/api/v5/repos/{UPSTREAM_OWNER}/{REPO}/pulls"
    data = json.dumps({
        "title": "fix: remove orphaned code fragments from split files",
        "body": "修复以下8个文件中孤立的代码片段问题：\n\n- split_files__extract_imports_block.py\n- split_files__extract_tool_config_block.py\n- split_files__build_file_content.py\n- split_files__generate_init_files.py\n- split_files__get_func_source.py\n- split_files__main.py\n- split_files__split_file.py\n- split_files__extract_logging_block.py\n\n这些文件在之前的PR中包含了从其他函数误复制的孤立代码片段，现已修复。",
        "head": f"{FORK_OWNER}:master",
        "base": "master"
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'Bearer {TOKEN}')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            pr_number = result.get('iid', 0)
            pr_url = f"https://atomgit.com/{UPSTREAM_OWNER}/{REPO}/merge_requests/{pr_number}"
            print(f"\n修复 PR 已创建: {pr_url}")
            print(f"PR 编号: #{pr_number}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"\nPR 创建失败: {error_body}")

    print("\n=== 完成 ===")


if __name__ == '__main__':
    main()
