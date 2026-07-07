from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import os
import re
import subprocess

from .utils import get_nginx_config_info, check_nginx_installation

# 导入工具函数
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_config_include')

def analyze_include_directives(body: str, base_dir: str = '') -> List[Dict[str, Union[str, int, bool]]]:
    """
    解析配置文件中的include指令

    参数:
        body: 配置文件内容
        base_dir: 配置文件所在目录，用于解析相对路径

    返回:
        list: 包含include指令信息的字典列表
    """
    includes = []

    try:
        # 查找所有include指令
        include_patterns = re.findall(r'include\s+([^\s;]+)', body)  # NOSONAR

        for i, pattern in enumerate(include_patterns):
            # 获取include指令在文件中的行号
            line_number = fetch_include_line_number(body, pattern, i)

            # 解析路径
            is_absolute = os.path.isabs(pattern)
            has_wildcard = '*' in pattern or '?' in pattern

            # 处理路径
            full_pattern = os.path.join(base_dir, pattern) if not is_absolute and base_dir else pattern
            includes.append({
                'index': i + 1,
                'pattern': pattern,
                'full_pattern': full_pattern,
                'is_absolute': is_absolute,
                'has_wildcard': has_wildcard,
                'line_number': line_number,
                'resolved_files': []
            })

        return includes

    except Exception as e:
        logger.error(f'解析include指令失败: {e}')
        return []

def fetch_include_line_number(body: str, pattern: str, occurrence: int) -> int:
    """
    获取include指令在文件中的行号

    参数:
        body: 文件内容
        pattern: include模式
        occurrence: 出现次数索引

    返回:
        int: 行号
    """
    try:
        lines = body.split('\n')
        count = 0

        for i, line in enumerate(lines):
            if re.search(rf'include\s+{re.escape(pattern)}', line):  # NOSONAR
                if count == occurrence:
                    return i + 1
                count += 1

        return -1

    except Exception as e:
        logger.error(f'获取include指令行号失败: {e}')
        return -1

def resolve_include_pattern(pattern: str) -> List[Dict[str, Union[str, bool, int]]]:
    """
    解析include模式，返回匹配的文件列表

    参数:
        pattern: include模式（可能包含通配符）

    返回:
        list: 包含匹配文件信息的字典列表
    """
    resolved_files = []

    try:
        # 如果没有通配符，直接检查文件是否存在
        if '*' not in pattern and '?' not in pattern:
            if os.path.isfile(pattern):
                file_stat = os.stat(pattern)
                resolved_files.append({
                    'path': pattern,
                    'exists': True,
                    'is_readable': os.access(pattern, os.R_OK),
                    'size': file_stat.st_size,
                    'modified_time': file_stat.st_mtime
                })
            else:
                resolved_files.append({
                    'path': pattern,
                    'exists': False,
                    'is_readable': False,
                    'error': '文件不存在'
                })
            return resolved_files

        # 处理通配符
        dir_path = os.path.dirname(pattern)
        file_pattern = os.path.basename(pattern)

        # 转换通配符为正则表达式
        regex_pattern = file_pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')  # NOSONAR
        regex_pattern = f'^{regex_pattern}$'

        # 检查目录是否存在
        if not os.path.exists(dir_path):
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'目录不存在: {dir_path}'
            })
            return resolved_files

        # 查找匹配的文件
        try:
            for file_name in os.listdir(dir_path):
                if re.match(regex_pattern, file_name):  # NOSONAR
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        file_stat = os.stat(file_path)
                        resolved_files.append({
                            'path': file_path,
                            'exists': True,
                            'is_readable': os.access(file_path, os.R_OK),
                            'size': file_stat.st_size,
                            'modified_time': file_stat.st_mtime
                        })
        except PermissionError:
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'没有权限读取目录: {dir_path}'
            })

        # 如果没有找到匹配的文件
        if not resolved_files:
            resolved_files.append({
                'path': pattern,
                'exists': False,
                'is_readable': False,
                'error': f'没有找到匹配的文件: {pattern}'
            })

        # 按修改时间排序（加载顺序）
        resolved_files.sort(key=lambda x: x.get('modified_time', 0))

        return resolved_files

    except Exception as e:
        logger.error(f'解析include模式失败: {e}')
        return [{
            'path': pattern,
            'exists': False,
            'is_readable': False,
            'error': f'解析失败: {e}'
        }]

def fetch_nested_includes(file_path: str, max_depth: int = 5, current_depth: int = 0, visited_files: set = None) -> Dict:
    """
    递归获取嵌套的include指令

    参数:
        file_path: 配置文件路径
        max_depth: 最大递归深度
        current_depth: 当前递归深度
        visited_files: 已访问的文件集合（防止循环引用）

    返回:
        dict: 包含嵌套include信息的字典
    """
    visited_files = set() if visited_files is None else visited_files
    # 防止循环引用
    if file_path in visited_files or current_depth >= max_depth:
        return {
            'file_path': file_path,
            'includes': [],
            'error': '已达到最大递归深度或检测到循环引用'
        }

    visited_files.add(file_path)

    try:
        # 读取文件内容
        body = Path(file_path).read_text()

        # 解析include指令
        base_dir = os.path.dirname(file_path)
        includes = analyze_include_directives(body, base_dir)

        # 递归处理每个include
        for include in includes:
            pattern = include['full_pattern']
            resolved_files = resolve_include_pattern(pattern)
            include['resolved_files'] = resolved_files

            # 递归处理每个解析出的文件
            for file_info in resolved_files:
                if file_info.get('exists', False) and file_info.get('is_readable', False):
                    nested_path = file_info['path']
                    nested_result = fetch_nested_includes(
                        nested_path,
                        max_depth,
                        current_depth + 1,
                        visited_files.copy()
                    )
                    file_info['nested_includes'] = nested_result

        return {
            'file_path': file_path,
            'includes': includes,
            'depth': current_depth
        }

    except Exception as e:
        logger.error(f'获取嵌套include失败: {e}')
        return {
            'file_path': file_path,
            'includes': [],
            'error': f'处理文件失败: {e}'
        }

def fetch_config_include_status() -> Dict:
    """
    获取Nginx配置include状态

    返回:
        dict: 包含include状态信息的字典
    """
    try:
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            return {
                'error': 'Nginx未安装',
                'suggestion': nginx_status.get('suggestion', '请安装Nginx')
            }

        # 获取主配置文件路径
        cfg_state = get_nginx_config_info()
        main_config_path = cfg_state.get('config_file', '/etc/nginx/nginx.conf')

        # 检查主配置文件是否存在
        if not os.path.exists(main_config_path):
            return {
                'error': f'主配置文件不存在: {main_config_path}',
                'suggestion': '请检查Nginx配置文件路径'
            }

        # 获取嵌套include信息
        include_tree = fetch_nested_includes(main_config_path)

        # 统计信息
        stats = {
            'total_include_directives': 0,
            'total_included_files': 0,
            'existing_files': 0,
            'missing_files': 0,
            'unreadable_files': 0
        }

        # 递归统计
        def count_includes(node):
            if 'includes' in node:
                stats['total_include_directives'] += len(node['includes'])

                for include in node['includes']:
                    if 'resolved_files' in include:
                        stats['total_included_files'] += len(include['resolved_files'])

                        for file_info in include['resolved_files']:
                            if file_info.get('exists', False):
                                stats['existing_files'] += 1
                                if not file_info.get('is_readable', False):
                                    stats['unreadable_files'] += 1
                            else:
                                stats['missing_files'] += 1

                    # 递归处理嵌套include
                    for file_info in include.get('resolved_files', []):
                        if file_info.get('exists', False) and 'nested_includes' in file_info:
                            count_includes(file_info['nested_includes'])

        count_includes(include_tree)

        # 检查配置语法
        config_test_result = subprocess.run(
            ['nginx', '-t'],
            capture_output=True,
            text=True,
            stderr=subprocess.STDOUT
        )

        config_status = {
            'syntax_valid': config_test_result.returncode == 0,
            'output': config_test_result.stdout.strip()
        }

        return {
            'main_config': main_config_path,
            'include_tree': include_tree,
            'statistics': stats,
            'config_status': config_status
        }

    except Exception as e:
        logger.error(f'获取配置include状态失败: {e}')
        return {
            'error': f'获取配置include状态失败: {e}'
        }

def flatten_include_tree(include_tree: Dict, flat_list: List = None, level: int = 0) -> List[Dict]:
    """
    将嵌套的include树展平为列表

    参数:
        include_tree: include树
        flat_list: 展平后的列表
        level: 当前层级

    返回:
        list: 展平后的include列表
    """
    flat_list = [] if flat_list is None else flat_list
    if 'includes' in include_tree:
        for include in include_tree['includes']:
            include_info = {
                'level': level,
                'pattern': include['pattern'],
                'line_number': include['line_number'],
                'is_absolute': include['is_absolute'],
                'has_wildcard': include['has_wildcard']
            }

            for file_info in include.get('resolved_files', []):
                file_entry = include_info.copy()
                file_entry.update({
                    'file_path': file_info['path'],
                    'exists': file_info.get('exists', False),
                    'is_readable': file_info.get('is_readable', False),
                    'size': file_info.get('size', 0),
                    'modified_time': file_info.get('modified_time', 0)
                })

                if 'error' in file_info:
                    file_entry['error'] = file_info['error']

                flat_list.append(file_entry)

                # 递归处理嵌套include
                if file_info.get('exists', False) and 'nested_includes' in file_info:
                    flatten_include_tree(file_info['nested_includes'], flat_list, level + 1)

    return flat_list

def fetch_nginx_config_include() -> Dict:
    """
    获取主配置中include的所有子配置路径、加载顺序、生效状态

    返回:
        dict: 包含include状态信息的字典
    """
    output = fetch_config_include_status()

    # 如果没有错误，添加展平的include列表
    if 'include_tree' in output:
        output['flat_includes'] = flatten_include_tree(output['include_tree'])

    return output

TOOL_CONFIG = {
    "name": "fetch_nginx_config_include",
    "description": "获取主配置中include的所有子配置路径、加载顺序、生效状态",
    "function": fetch_nginx_config_include,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
