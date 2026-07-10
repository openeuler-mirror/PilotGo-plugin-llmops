from datetime import datetime
import logging
import os
import re
import subprocess

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_main')

def fetch_nginx_config_main():
    """
    获取Nginx主配置文件(nginx.conf)的完整内容并格式化输出
    """
    try:
        output = []
        output.append('=== Nginx主配置文件内容 ===')

        # 获取nginx配置信息
        cfg_state = get_nginx_config_info()
        config_file = cfg_state.get('config_file', '')

        if not config_file or config_file == 'Unknown' or config_file == '获取失败':
            output.append('无法获取Nginx配置文件路径')
            return '\n'.join(output)

        # 检查配置文件是否存在
        if not os.path.exists(config_file):
            output.append(f'配置文件不存在: {config_file}')
            return '\n'.join(output)

        # 读取配置文件内容
        with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
            body = f.read()

        # 添加配置文件路径信息
        output.append(f'配置文件路径: {config_file}')
        output.append(f'配置测试状态: {cfg_state.get("config_test", "未知")}')
        output.append(f'文件大小: {os.path.getsize(config_file)} 字节')

        # 获取文件修改时间
        mtime = os.path.getmtime(config_file)
        mod_time = datetime.fromtimestamp(mtime)
        output.append(f'最后修改时间: {mod_time.strftime("%Y-%m-%d %H:%M:%S")}')

        output.append('\n--- 配置文件内容 ---')

        # 格式化配置文件内容
        formatted_content = render_nginx_config(body)
        output.append(formatted_content)

        # 解析并显示配置文件结构
        output.append('\n--- 配置文件结构分析 ---')
        structure = examine_config_structure(body)
        output.append(structure)

        output.append('\n======================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取Nginx主配置文件失败: {e}')
        return f'获取Nginx主配置文件失败: {e}'

def render_nginx_config(body):
    """格式化Nginx配置文件内容，添加适当的缩进和行号"""
    try:
        lines = body.split('\n')
        formatted_lines = []
        indent_level = 0
        line_number = 1

        for line in lines:
            # 保留原始行，但添加行号
            formatted_line = f"{line_number:4d}: {line}"

            # 检查是否是包含大括号的行
            if '{' in line and '}' in line:
                # 同一行包含开闭括号，不改变缩进
                pass
            elif '{' in line:
                # 包含开括号，增加缩进
                indent_level += 1
            elif '}' in line:
                # 包含闭括号，减少缩进
                indent_level = max(0, indent_level - 1)

            formatted_lines.append(formatted_line)
            line_number += 1

        return '\n'.join(formatted_lines)
    except Exception as e:
        logger.error(f'格式化配置文件失败: {e}')
        return body