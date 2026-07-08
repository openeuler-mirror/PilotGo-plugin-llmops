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
logger = logging.getLogger('nginx_config_item')

def fetch_config_file_paths(config_type: str = "main", site_name: str = None) -> Dict[str, Union[str, List[str]]]:
    """
    获取配置文件路径

    参数:
        config_type: 配置类型 (main/site/module)
        site_name: 站点名称 (当config_type为site时使用)

    返回:
        dict: 包含配置文件路径的字典
    """
    try:
        # 获取主配置文件路径
        cfg_state = get_nginx_config_info()
        main_config_path = cfg_state.get('config_file', '/etc/nginx/nginx.conf')

        output = {
            'main_config': main_config_path,
            'config_files': []
        }

        if config_type == "main":
            output['config_files'] = [main_config_path]

        elif config_type == "site":
            if not site_name:
                # 如果没有指定站点，返回所有站点配置
                output['config_files'] = fetch_all_site_configs(main_config_path)
            else:
                # 查找指定站点配置
                site_config = locate_site_config(main_config_path, site_name)
                if site_config:
                    output['config_files'] = [site_config]
                else:
                    output['error'] = f"未找到站点 '{site_name}' 的配置文件"

        elif config_type == "module":
            # 模块配置通常在主配置文件中
            output['config_files'] = [main_config_path]

        return output

    except Exception as e:
        logger.error(f'获取配置文件路径失败: {e}')
        return {
            'main_config': 'Unknown',
            'config_files': [],
            'error': f'获取配置文件路径失败: {e}'
        }

def fetch_all_site_configs(main_config_path: str) -> List[str]:
    """
    获取所有站点配置文件路径

    参数:
        main_config_path: 主配置文件路径

    返回:
        list: 站点配置文件路径列表
    """
    site_configs = []

    try:
        # 读取主配置文件
        body = Path(main_config_path).read_text()

        # 查找include指令
        include_patterns = re.findall(r'include\s+([^\s;]+)', body)  # NOSONAR

        for pattern in include_patterns:
            # 处理通配符
            if '*' in pattern:
                # 获取目录路径
                dir_path = os.path.dirname(pattern)
                if not os.path.isabs(dir_path):
                    # 相对路径，基于主配置文件所在目录
                    dir_path = os.path.join(os.path.dirname(main_config_path), dir_path)

                # 获取文件名模式
                file_pattern = os.path.basename(pattern)

                # 查找匹配的文件
                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if re.match(file_pattern.replace('*', '.*'), file):  # NOSONAR
                            full_path = os.path.join(dir_path, file)
                            if os.path.isfile(full_path):
                                site_configs.append(full_path)
            else:
                # 具体文件路径
                if not os.path.isabs(pattern):
                    pattern = os.path.join(os.path.dirname(main_config_path), pattern)

                if os.path.isfile(pattern):
                    site_configs.append(pattern)

        # 如果没有找到站点配置，尝试常见路径
        if not site_configs:
            common_paths = [
                '/etc/nginx/sites-enabled/*',
                '/etc/nginx/conf.d/*.conf',
                '/usr/local/nginx/conf/vhosts/*.conf'
            ]

            for path_pattern in common_paths:
                dir_path = os.path.dirname(path_pattern)
                file_pattern = os.path.basename(path_pattern)

                if os.path.exists(dir_path):
                    for file in os.listdir(dir_path):
                        if re.match(file_pattern.replace('*', '.*'), file):  # NOSONAR
                            full_path = os.path.join(dir_path, file)
                            if os.path.isfile(full_path):
                                site_configs.append(full_path)

        return site_configs

    except Exception as e:
        logger.error(f'获取站点配置文件列表失败: {e}')
        return []

def locate_site_config(main_config_path: str, site_name: str) -> Optional[str]:
    """
    查找指定站点的配置文件

    参数:
        main_config_path: 主配置文件路径
        site_name: 站点名称

    返回:
        str: 站点配置文件路径，如果未找到则返回None
    """
    try:
        # 获取所有站点配置
        site_configs = fetch_all_site_configs(main_config_path)

        # 查找匹配的站点配置
        for config_path in site_configs:
            body = Path(config_path).read_text()

            # 查找server_name指令
            server_names = re.findall(r'server_name\s+([^;]+)', body)  # NOSONAR
            for names in server_names:
                name_list = [name.strip() for name in names.split()]
                if site_name in name_list:
                    return config_path

        # 如果没有找到，尝试根据文件名匹配
        for config_path in site_configs:
            filename = os.path.basename(config_path)
            if site_name in filename:
                return config_path

        return None

    except Exception as e:
        logger.error(f'查找站点配置失败: {e}')
        return None

def analyze_config_value(body: str, item_name: str, context: str = None) -> List[Dict[str, Union[str, int]]]:
    """
    解析配置项的值

    参数:
        body: 配置文件内容
        item_name: 配置项名称
        context: 上下文 (http/server/location等)

    返回:
        list: 包含配置项值的字典列表
    """
    results = []

    try:
        # 构建正则表达式
        if context:
            # 在指定上下文中查找
            pattern = rf'{context}\s*\{{[^}}]*{item_name}\s+([^;]+)[^}}]*\}}'  # NOSONAR
            matches = re.findall(pattern, body, re.DOTALL)  # NOSONAR
        else:
            # 全局查找
            pattern = rf'{item_name}\s+([^;]+)'  # NOSONAR
            matches = re.findall(pattern, body)  # NOSONAR

        # 处理匹配结果
        for i, match in enumerate(matches):
            val = match.strip()

            # 尝试解析数值
            numeric_value = None
            try:
                # 提取数字部分
                numeric_match = re.search(r'(\d+)', val)  # NOSONAR
                if numeric_match:
                    numeric_value = int(numeric_match.group(1))
            except Exception:
                pass

            results.append({
                'index': i + 1,
                'val': val,
                'numeric_value': numeric_value,
                'line': fetch_line_number(body, item_name, i)
            })

        return results

    except Exception as e:
        logger.error(f'解析配置项值失败: {e}')
        return []

def fetch_line_number(body: str, item_name: str, occurrence: int) -> int:
    """
    获取配置项在文件中的行号

    参数:
        body: 文件内容
        item_name: 配置项名称
        occurrence: 出现次数索引

    返回:
        int: 行号
    """
    try:
        lines = body.split('\n')
        count = 0

        for i, line in enumerate(lines):
            if re.search(rf'\b{item_name}\b', line):  # NOSONAR
                if count == occurrence:
                    return i + 1
                count += 1

        return -1

    except Exception as e:
        logger.error(f'获取行号失败: {e}')
        return -1

def fetch_config_item(config_type: str, item_name: str, site_name: str = None, context: str = None) -> Dict:
    """
    获取指定配置项的值

    参数:
        config_type: 配置类型 (main/site/module)
        item_name: 配置项名称
        site_name: 站点名称 (当config_type为site时使用)
        context: 上下文 (http/server/location等)

    返回:
        dict: 包含配置项值的字典
    """
    try:
        # 检查Nginx安装状态
        nginx_status = check_nginx_installation()
        if not nginx_status.get('installed', False):
            return {
                'error': 'Nginx未安装',
                'suggestion': nginx_status.get('suggestion', '请安装Nginx')
            }

        # 获取配置文件路径
        config_paths = fetch_config_file_paths(config_type, site_name)

        if 'error' in config_paths:
            return config_paths

        # 初始化结果
        output = {
            'config_type': config_type,
            'item_name': item_name,
            'values': [],
            'files_analyzed': 0,
            'total_occurrences': 0
        }

        if config_type == 'site' and site_name:
            output['site_name'] = site_name

        if context:
            output['context'] = context

        # 分析每个配置文件
        for config_file in config_paths['config_files']:
            try:
                # 读取配置文件
                body = Path(config_file).read_text()

                # 解析配置项
                values = analyze_config_value(body, item_name, context)

                if values:
                    output['values'].append({
                        'file': config_file,
                        'values': values
                    })
                    output['total_occurrences'] += len(values)

                output['files_analyzed'] += 1

            except Exception as e:
                logger.error(f'分析配置文件 {config_file} 失败: {e}')
                continue

        # 如果没有找到任何值，提供一些常见配置项的默认值
        if not output['values']:
            default_values = fetch_default_values(item_name)
            if default_values:
                output['default_values'] = default_values
                output['note'] = f"未找到配置项 '{item_name}'，以下是默认值参考"

        return output

    except Exception as e:
        logger.error(f'获取配置项失败: {e}')
        return {
            'error': f'获取配置项失败: {e}'
        }

def fetch_default_values(item_name: str) -> Optional[Dict[str, Union[str, int]]]:
    """
    获取常见配置项的默认值

    参数:
        item_name: 配置项名称

    返回:
        dict: 默认值字典，如果不知道则返回None
    """
    defaults = {
        'worker_processes': {'val': 'auto', 'numeric_value': None, 'description': '自动设置为CPU核心数'},
        'worker_connections': {'val': '1024', 'numeric_value': 1024, 'description': '每个工作进程的最大连接数'},
        'keepalive_timeout': {'val': '65', 'numeric_value': 65, 'description': '保持连接超时时间(秒)'},
        'client_max_body_size': {'val': '1m', 'numeric_value': 1, 'description': '客户端请求体最大大小'},
        'sendfile': {'val': 'on', 'numeric_value': None, 'description': '是否启用sendfile'},
        'tcp_nopush': {'val': 'on', 'numeric_value': None, 'description': '是否启用tcp_nopush'},
        'tcp_nodelay': {'val': 'on', 'numeric_value': None, 'description': '是否启用tcp_nodelay'},
        'gzip': {'val': 'on', 'numeric_value': None, 'description': '是否启用gzip压缩'},
        'gzip_min_length': {'val': '1000', 'numeric_value': 1000, 'description': '启用压缩的最小响应大小'},
        'gzip_types': {'val': 'text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript', 'numeric_value': None, 'description': '启用压缩的MIME类型'},
        'listen': {'val': '80', 'numeric_value': 80, 'description': '默认监听端口'},
        'server_name': {'val': 'localhost', 'numeric_value': None, 'description': '默认服务器名称'},
        'root': {'val': '/usr/share/nginx/html', 'numeric_value': None, 'description': '默认根目录'},
        'index': {'val': 'index.html index.htm', 'numeric_value': None, 'description': '默认索引文件'},
        'access_log': {'val': '/var/log/nginx/access.log', 'numeric_value': None, 'description': '默认访问日志路径'},
        'error_log': {'val': '/var/log/nginx/error.log', 'numeric_value': None, 'description': '默认错误日志路径'}
    }

    return defaults.get(item_name)