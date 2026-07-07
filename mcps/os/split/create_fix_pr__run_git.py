#!/usr/bin/env python3

import os
import json
import urllib.request
import base64


def run_git(cmd, cwd=FORK_REPO_PATH):
    """执行 git 命令"""
    import subprocess
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  git 错误: {result.stderr.strip()}")
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
