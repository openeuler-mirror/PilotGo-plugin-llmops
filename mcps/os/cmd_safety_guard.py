import os
import re
import subprocess

def has_dangerous_chars(input_str, allow_space=False):
    """
    检查字符串是否包含危险字符（命令注入风险）

    参数:
        input_str: 待检查的字符串
        allow_space: 是否允许空格（默认 False，因为空格常用于命令注入）

    返回:
        bool: 如果包含危险字符返回 True，否则返回 False

    危险字符包括:
        ; - 命令分隔符
        | - 管道符
        & - 后台执行/逻辑与
        $ - 变量替换
        ` - 命令替换
        \\n - 换行符
        \\r - 回车符
        > - 重定向输出
        < - 重定向输入
        ( ) - 子 shell
        { } - 命令组
    """
    if not input_str:
        return False

    # 定义危险字符模式
    harmful_pattern = r'[;|&$`><()\{\}]'

    # 如果不允许空格，也检查空格
    if not allow_space:
        harmful_pattern = r'[;|&$`><()\{\}\s]'

    return bool(re.search(harmful_pattern, input_str))