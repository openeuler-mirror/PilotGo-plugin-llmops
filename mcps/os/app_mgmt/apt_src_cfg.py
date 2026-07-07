import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_apt_source.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_apt_source')

def fetch_app_apt_source(source_info=None):
    """
    采集APT源配置

    参数:
        source_info: 信息类型，可选值：
            - 'enabled': 启用的源
            - 'disabled': 禁用的源
            - 'components': 源组件信息
            - None: 获取所有信息

    返回:
        格式化的APT源配置信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== APT源配置信息 ===')

        # 检查系统是否支持APT
        if not is_apt_based_system():
            return "当前系统不是基于APT的系统（如Ubuntu/Debian）"

        # 获取APT源配置
        sources = fetch_apt_sources()

        # 根据参数返回不同信息
        if source_info == 'enabled':
            enabled_sources = [source for source in sources if source['enabled']]
            if enabled_sources:
                output.append(f"启用的源数量: {len(enabled_sources)}")
                for source in enabled_sources:
                    output.append(f"\n{source['name']}:")
                    output.append(f"  源地址: {source['uri']}")
                    output.append(f"  发行版代号: {source['distribution']}")
                    output.append(f"  组件: {', '.join(source['components'])}")
            else:
                output.append("没有启用的APT源")
            output.append('=====================')
            return '\n'.join(output)
        elif source_info == 'disabled':
            disabled_sources = [source for source in sources if not source['enabled']]
            if disabled_sources:
                output.append(f"禁用的源数量: {len(disabled_sources)}")
                for source in disabled_sources:
                    output.append(f"\n{source['name']}:")
                    output.append(f"  源地址: {source['uri']}")
                    output.append(f"  发行版代号: {source['distribution']}")
                    output.append(f"  组件: {', '.join(source['components'])}")
            else:
                output.append("没有禁用的APT源")
            output.append('=====================')
            return '\n'.join(output)
        elif source_info == 'components':
            if sources:
                output.append("APT源组件信息:")
                for source in sources:
                    output.append(f"\n{source['name']}:")
                    output.append(f"  状态: {'启用' if source['enabled'] else '禁用'}")
                    output.append(f"  组件: {', '.join(source['components'])}")
            else:
                output.append("未检测到APT源配置")
            output.append('=====================')
            return '\n'.join(output)
        else:
            # 获取所有信息
            if sources:
                enabled_count = len([source for source in sources if source['enabled']])
                disabled_count = len([source for source in sources if not source['enabled']])

                output.append(f"总源数量: {len(sources)}")
                output.append(f"启用的源: {enabled_count}")
                output.append(f"禁用的源: {disabled_count}")

                # 详细信息
                output.append("\n详细源配置:")
                for source in sources:
                    output.append(f"\n{source['name']}:")
                    output.append(f"  状态: {'启用' if source['enabled'] else '禁用'}")
                    output.append(f"  源地址: {source['uri']}")
                    output.append(f"  发行版代号: {source['distribution']}")
                    output.append(f"  组件: {', '.join(source['components'])}")
                    output.append(f"  类型: {source.get('type', 'deb')}")
                    output.append(f"  架构: {', '.join(source.get('arch', []))}")
            else:
                output.append("未检测到APT源配置")

            output.append('=====================')
            return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取APT源配置失败: {e}')
        return f'获取APT源配置失败: {e}'
def is_apt_based_system():
    """
    检查系统是否是基于APT的系统

    返回:
        bool: 是否是基于APT的系统
    """
    try:
        # 检查是否存在apt命令
        output = subprocess.run(['which', 'apt'], capture_output=True, text=True)
        if output.returncode == 0:
            return True

        # 检查系统发行版
        if os.path.exists('/etc/debian_version'):
            return True

        # 检查系统类型
        distro = platform.platform().lower()
        return any(keyword in distro for keyword in ['ubuntu', 'debian'])

    except Exception:
        return False
def fetch_apt_sources():
    """
    获取所有APT源配置

    返回:
        源配置列表
    """
    try:
        sources = []

        # 检查APT源配置目录
        source_dirs = ['/etc/apt/sources.list.d', '/etc/apt']
        source_files = []

        # 添加sources.list文件
        sources_list_file = '/etc/apt/sources.list'
        if os.path.exists(sources_list_file):
            source_files.append(sources_list_file)

        # 添加sources.list.d目录下的文件
        sources_list_d_dir = '/etc/apt/sources.list.d'
        if os.path.exists(sources_list_d_dir):
            for file in os.listdir(sources_list_d_dir):
                if file.endswith('.list'):
                    source_files.append(os.path.join(sources_list_d_dir, file))

        # 解析配置文件
        for source_file in source_files:
            file_sources = analyze_source_file(source_file)
            sources.extend(file_sources)

        return sources

    except Exception as e:
        logger.error(f'获取APT源配置失败: {e}')
        return []
def analyze_source_file(file_path):
    """
    解析APT源配置文件

    参数:
        file_path: 配置文件路径

    返回:
        源配置列表
    """
    try:
        sources = []

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue

            # 解析源配置行
            source_info = analyze_source_line(line, file_path, line_num)
            if source_info:
                sources.append(source_info)

        return sources

    except Exception as e:
        logger.error(f'解析APT源文件失败 {file_path}: {e}')
        return []
def analyze_source_line(line, file_path, line_num):
    """
    解析单行APT源配置

    参数:
        line: 配置行
        file_path: 文件路径
        line_num: 行号

    返回:
        源配置字典
    """
    try:
        # 基本格式: deb [选项] uri distribution [component1] [component2] ...
        parts = line.split()

        if not parts:
            return None

        source_info = {
            'name': f"{os.path.basename(file_path)}:{line_num}",
            'enabled': not line.startswith('#'),
            'type': parts[0],
            'uri': '',
            'distribution': '',
            'components': [],
            'arch': []
        }

        # 解析选项部分
        if parts[1].startswith('['):
            # 有选项
            option_end = line.find(']')
            if option_end != -1:
                options = line[line.find('[')+1:option_end].split()
                for option in options:
                    if '=' in option:
                        key, value = option.split('=', 1)
                        if key == 'arch':
                            source_info['arch'] = value.split(',')

            # 解析uri和distribution
            remaining = line[option_end+1:].strip().split()
            if len(remaining) >= 2:
                source_info['uri'] = remaining[0]
                source_info['distribution'] = remaining[1]
                if len(remaining) > 2:
                    source_info['components'] = remaining[2:]
        else:
            # 无选项
            if len(parts) >= 3:
                source_info['uri'] = parts[1]
                source_info['distribution'] = parts[2]
                if len(parts) > 3:
                    source_info['components'] = parts[3:]

        return source_info

    except Exception as e:
        logger.error(f'解析APT源配置行失败 {file_path}:{line_num}: {e}')
        return None

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_app_apt_source",
    "function": fetch_app_apt_source,
    "description": "采集APT源配置（所有启用/禁用的APT源/源地址/发行版代号/组件）",
    "parameters": {
        "type": "object",
        "properties": {
            "source_info": {
                "type": "string",
                "description": "信息类型，可选值：enabled（启用的源）、disabled（禁用的源）、components（源组件信息），不指定则获取所有信息",
                "enum": ["enabled", "disabled", "components"]
            }
        },
        "required": []
    }
}
