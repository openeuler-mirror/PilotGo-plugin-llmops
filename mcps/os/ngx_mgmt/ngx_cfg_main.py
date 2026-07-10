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

def examine_config_structure(body):
    """分析配置文件结构"""
    try:
        structure = []

        # 解析全局配置
        global_configs = derive_global_configs(body)
        if global_configs:
            structure.append('全局配置:')
            for config in global_configs:
                structure.append(f"  {config}")

        # 解析events块
        events_configs = derive_events_configs(body)
        if events_configs:
            structure.append('\nevents块配置:')
            for config in events_configs:
                structure.append(f"  {config}")

        # 解析http块
        http_configs = derive_http_configs(body)
        if http_configs:
            structure.append('\nhttp块配置:')
            for config in http_configs:
                structure.append(f"  {config}")

        # 解析server块
        server_configs = derive_server_configs(body)
        if server_configs:
            structure.append('\nserver块配置:')
            for config in server_configs:
                structure.append(f"  {config}")

        # 解析location块
        location_configs = derive_location_configs(body)
        if location_configs:
            structure.append('\nlocation块配置:')
            for config in location_configs:
                structure.append(f"  {config}")

        # 解析include指令
        include_configs = derive_include_configs(body)
        if include_configs:
            structure.append('\ninclude指令:')
            for config in include_configs:
                structure.append(f"  {config}")

        return '\n'.join(structure) if structure else '无法解析配置文件结构'
    except Exception as e:
        logger.error(f'分析配置文件结构失败: {e}')
        return f'分析配置文件结构失败: {e}'

def derive_global_configs(body):
    """提取全局配置"""
    try:
        global_configs = []

        # 常见的全局配置项
        patterns = {
            'user': r'user\s+([^;]+);',
            'worker_processes': r'worker_processes\s+([^;]+);',
            'worker_cpu_affinity': r'worker_cpu_affinity\s+([^;]+);',
            'worker_rlimit_nofile': r'worker_rlimit_nofile\s+([^;]+);',
            'error_log': r'error_log\s+([^;]+);',
            'pid': r'pid\s+([^;]+);',
            'worker_priority': r'worker_priority\s+([^;]+);',
            'worker_rlimit_core': r'worker_rlimit_core\s+([^;]+);',
            'daemon': r'daemon\s+([^;]+);',
            'master_process': r'master_process\s+([^;]+);',
            'debug_points': r'debug_points\s+([^;]+);'
        }

        for config_name, pattern in patterns.items():
            match = re.search(pattern, body)  # NOSONAR
            if match:
                global_configs.append(f"{config_name}: {match.group(1).strip()}")

        return global_configs
    except Exception as e:
        logger.error(f'提取全局配置失败: {e}')
        return []

def derive_events_configs(body):
    """提取events块配置"""
    try:
        events_configs = []

        # 提取events块内容
        events_match = re.search(r'events\s*\{([^}]*)\}', body, re.DOTALL)  # NOSONAR
        if not events_match:
            return events_configs

        events_content = events_match.group(1)

        # 常见的events配置项
        patterns = {
            'worker_connections': r'worker_connections\s+([^;]+);',
            'use': r'use\s+([^;]+);',
            'multi_accept': r'multi_accept\s+([^;]+);',
            'accept_mutex': r'accept_mutex\s+([^;]+);',
            'accept_mutex_delay': r'accept_mutex_delay\s+([^;]+);',
            'debug_connection': r'debug_connection\s+([^;]+);'
        }

        for config_name, pattern in patterns.items():
            match = re.search(pattern, events_content)  # NOSONAR
            if match:
                events_configs.append(f"{config_name}: {match.group(1).strip()}")

        return events_configs
    except Exception as e:
        logger.error(f'提取events配置失败: {e}')
        return []

def derive_http_configs(body):
    """提取http块配置"""
    try:
        http_configs = []

        # 提取http块内容（不包括嵌套的server和location块）
        http_pattern = r'http\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}'  # NOSONAR
        http_match = re.search(http_pattern, body, re.DOTALL)  # NOSONAR
        if not http_match:
            return http_configs

        http_content = http_match.group(1)

        # 移除server块和location块，只保留http级别的配置
        server_block_pattern = r'server\s*\{[^{}]*\}'  # NOSONAR
        http_content = re.sub(server_block_pattern, '', http_content, flags=re.DOTALL)  # NOSONAR

        # 常见的http配置项
        patterns = {
            'sendfile': r'sendfile\s+([^;]+);',
            'tcp_nopush': r'tcp_nopush\s+([^;]+);',
            'tcp_nodelay': r'tcp_nodelay\s+([^;]+);',
            'keepalive_timeout': r'keepalive_timeout\s+([^;]+);',
            'keepalive_requests': r'keepalive_requests\s+([^;]+);',
            'client_header_timeout': r'client_header_timeout\s+([^;]+);',
            'client_body_timeout': r'client_body_timeout\s+([^;]+);',
            'send_timeout': r'send_timeout\s+([^;]+);',
            'client_max_body_size': r'client_max_body_size\s+([^;]+);',
            'default_type': r'default_type\s+([^;]+);',
            'access_log': r'access_log\s+([^;]+);',
            'error_log': r'error_log\s+([^;]+);',
            'gzip': r'gzip\s+([^;]+);',
            'gzip_vary': r'gzip_vary\s+([^;]+);',
            'gzip_proxied': r'gzip_proxied\s+([^;]+);',
            'gzip_comp_level': r'gzip_comp_level\s+([^;]+);',
            'gzip_types': r'gzip_types\s+([^;]+);',
            'root': r'root\s+([^;]+);',
            'index': r'index\s+([^;]+);'
        }

        for config_name, pattern in patterns.items():
            match = re.search(pattern, http_content)  # NOSONAR
            if match:
                http_configs.append(f"{config_name}: {match.group(1).strip()}")

        return http_configs
    except Exception as e:
        logger.error(f'提取http配置失败: {e}')
        return []