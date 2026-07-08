from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import glob
import logging
import os
import re
import shutil
import subprocess

from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_config_info, execute_command, verify_nginx_installation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_log_path_modify')

def modify_nginx_log_paths(cfg_filepath: Optional[str] = None,
                          access_log_path: Optional[str] = None,
                          error_log_path: Optional[str] = None,
                          backup_original: bool = True) -> Dict:
    """
    修改访问日志/错误日志的存储路径、文件名称

    参数:
        cfg_filepath: Nginx 配置文件路径，如果为 None 则自动检测
        access_log_path: 新的访问日志路径（包含文件名）
        error_log_path: 新的错误日志路径（包含文件名）
        backup_original: 是否备份原始配置文件

    返回:
        Dict: 包含修改结果的字典
    """
    try:
        # 验证参数
        if not access_log_path and not error_log_path:
            return {
                'success': False,
                'message': '必须提供至少一个日志路径参数',
                'changes_made': [],
                'backup_path': None
            }

        # 安全验证：验证 access_log_path 路径参数（如果提供，允许绝对路径）
        if access_log_path is not None:
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_nginx_log_paths: access_log_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'message': f'访问日志路径不安全：{error_msg}',
                    'changes_made': [],
                    'backup_path': None
                }

        # 安全验证：验证 error_log_path 路径参数（如果提供，允许绝对路径）
        if error_log_path is not None:
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_nginx_log_paths: error_log_path 路径验证失败：{error_msg}")
                return {
                    'success': False,
                    'message': f'错误日志路径不安全：{error_msg}',
                    'changes_made': [],
                    'backup_path': None
                }

        # 检查Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'changes_made': [],
                'backup_path': None
            }

        # 获取配置文件路径
        if not cfg_filepath:
            cfg_filepath = fetch_nginx_config_path()
            if not cfg_filepath:
                return {
                    'success': False,
                    'message': '无法自动检测Nginx配置文件路径',
                    'changes_made': [],
                    'backup_path': None
                }

        # 验证配置文件存在
        if not os.path.exists(cfg_filepath):
            return {
                'success': False,
                'message': f'配置文件不存在: {cfg_filepath}',
                'changes_made': [],
                'backup_path': None
            }

        # 备份原始配置文件
        backup_path = None
        if backup_original:
            backup_path = save_config_file(cfg_filepath)
            if not backup_path:
                return {
                    'success': False,
                    'message': '配置文件备份失败',
                    'changes_made': [],
                    'backup_path': None
                }

        # 读取配置文件内容
        original_content = Path(cfg_filepath).read_text(encoding='utf-8')

        # 解析当前日志配置
        current_logs = analyze_current_log_configs(original_content, cfg_filepath)

        # 修改日志路径
        modified_content, changes = modify_log_paths_in_content(
            original_content,
            access_log_path,
            error_log_path,
            current_logs
        )

        # 如果没有修改，直接返回
        if not changes:
            return {
                'success': True,
                'message': '未检测到需要修改的日志配置',
                'changes_made': [],
                'backup_path': backup_path
            }

        # 写入修改后的配置
        with open(cfg_filepath, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        # 验证配置语法
        syntax_check = verify_nginx_syntax(cfg_filepath)
        if not syntax_check['valid']:
            # 语法错误，恢复备份
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, cfg_filepath)

            return {
                'success': False,
                'message': '配置语法错误，已恢复原始配置',
                'changes_made': changes,
                'backup_path': backup_path,
                'syntax_errors': syntax_check['errors']
            }

        # 创建新的日志目录（如果需要）
        build_log_directories(access_log_path, error_log_path)

        # 重载Nginx配置
        reload_result = reload_nginx_config()

        return {
            'success': True,
            'message': '日志路径修改完成',
            'changes_made': changes,
            'backup_path': backup_path,
            'syntax_check': syntax_check,
            'reload_result': reload_result,
            'new_paths': {
                'access_log': access_log_path,
                'error_log': error_log_path
            }
        }

    except Exception as e:
        logger.error(f'修改日志路径失败: {e}')
        # 发生错误时恢复备份
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, cfg_filepath)
            except Exception as restore_error:
                logger.error(f'恢复备份失败: {restore_error}')

        return {
            'success': False,
            'message': f'修改失败: {e}',
            'changes_made': [],
            'backup_path': backup_path
        }

def verify_nginx_installation() -> Dict:
    """检查Nginx安装状态"""
    try:
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode != 0:
            return {
                'installed': False,
                'suggestion': '请使用包管理器安装Nginx (如: apt install nginx 或 yum install nginx)'
            }

        ngx_bin_path = output.stdout.strip()
        if not os.path.exists(ngx_bin_path):
            return {
                'installed': False,
                'suggestion': 'Nginx二进制文件不存在，请重新安装'
            }

        return {'installed': True, 'path': ngx_bin_path}

    except Exception as e:
        logger.error(f'检查Nginx安装状态失败: {e}')
        return {
            'installed': False,
            'suggestion': f'检查安装状态时出错: {e}'
        }

def fetch_nginx_config_path() -> Optional[str]:
    """获取Nginx配置文件路径"""
    try:
        # 尝试通过nginx -t命令获取配置文件路径
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
        if output.returncode == 0 or output.returncode == 1:  # 允许配置错误但仍获取路径
            output = output.stdout if output.stdout else output.stderr
            config_match = re.search(r'file ([^\s]+) test', output)  # NOSONAR
            if config_match:
                return config_match.group(1)

        # 常见配置文件路径
        common_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/usr/local/etc/nginx/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        return None

    except Exception as e:
        logger.error(f'获取Nginx配置路径失败: {e}')
        return None

def save_config_file(cfg_filepath: str) -> Optional[str]:
    """备份配置文件"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"save_config_file: cfg_filepath 路径验证失败：{error_msg}")
            return None

        timestamp = subprocess.getoutput('date +%Y%m%d_%H%M%S')
        backup_dir = '/tmp/nginx_config_backups'  # NOSONAR
        Path(backup_dir).mkdir(exist_ok=True)

        backup_filename = f"{os.path.basename(cfg_filepath)}.backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_filename)

        shutil.copy2(cfg_filepath, backup_path)
        return backup_path

    except Exception as e:
        logger.error(f'备份配置文件失败: {e}')
        return None

def analyze_current_log_configs(body: str, cfg_filepath: str) -> Dict:
    """解析当前日志配置"""
    logs_info = {
        'access_logs': [],
        'error_logs': [],
        'include_files': []
    }

    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"analyze_current_log_configs: cfg_filepath 路径验证失败：{error_msg}")
            return logs_info

        # 解析主配置文件中的日志配置
        access_log_pattern = r'access_log\s+([^;]+);'  # NOSONAR
        error_log_pattern = r'error_log\s+([^;]+);'  # NOSONAR

        # 主配置文件中的日志配置
        access_matches = re.findall(access_log_pattern, body)  # NOSONAR
        error_matches = re.findall(error_log_pattern, body)  # NOSONAR

        for match in access_matches:
            logs_info['access_logs'].append({
                'path': match.strip(),
                'file': cfg_filepath,
                'type': 'main'
            })

        for match in error_matches:
            logs_info['error_logs'].append({
                'path': match.strip(),
                'file': cfg_filepath,
                'type': 'main'
            })

        # 解析 include 文件
        include_pattern = r'include\s+([^;]+);'  # NOSONAR
        include_matches = re.findall(include_pattern, body)  # NOSONAR

        config_dir = os.path.dirname(cfg_filepath)
        for include in include_matches:
            include_path = include.strip().strip('"\'').strip()
            if not os.path.isabs(include_path):
                include_path = os.path.join(config_dir, include_path)

            # 处理通配符
            if '*' in include_path:
                included_files = glob.glob(include_path)
                for file in included_files:
                    if os.path.isfile(file):
                        logs_info['include_files'].append(file)
            elif os.path.exists(include_path):
                if os.path.isfile(include_path):
                    logs_info['include_files'].append(include_path)
                elif os.path.isdir(include_path):
                    for file in os.listdir(include_path):
                        if file.endswith('.conf'):
                            logs_info['include_files'].append(os.path.join(include_path, file))

        # 解析include文件中的日志配置
        for include_file in logs_info['include_files']:
            try:
                include_content = Path(include_file).read_text(encoding='utf-8')

                include_access_matches = re.findall(access_log_pattern, include_content)  # NOSONAR
                include_error_matches = re.findall(error_log_pattern, include_content)  # NOSONAR

                for match in include_access_matches:
                    logs_info['access_logs'].append({
                        'path': match.strip(),
                        'file': include_file,
                        'type': 'include'
                    })

                for match in include_error_matches:
                    logs_info['error_logs'].append({
                        'path': match.strip(),
                        'file': include_file,
                        'type': 'include'
                    })

            except Exception as e:
                logger.warning(f'解析include文件失败 {include_file}: {e}')
                continue

        return logs_info

    except Exception as e:
        logger.error(f'解析日志配置失败: {e}')
        return logs_info

def modify_log_paths_in_content(body: str,
                               access_log_path: Optional[str],
                               error_log_path: Optional[str],
                               current_logs: Dict) -> Tuple[str, List[Dict]]:
    """在配置内容中修改日志路径"""
    changes = []
    modified_content = body

    try:
        # 安全验证：验证 access_log_path 路径参数（如果提供，允许绝对路径）
        if access_log_path is not None:
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_log_paths_in_content: access_log_path 路径验证失败：{error_msg}")
                return body, changes

        # 安全验证：验证 error_log_path 路径参数（如果提供，允许绝对路径）
        if error_log_path is not None:
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"modify_log_paths_in_content: error_log_path 路径验证失败：{error_msg}")
                return body, changes

        # 修改访问日志路径
        if access_log_path:
            # 处理主配置文件中的访问日志
            access_log_pattern = r'(access_log\s+)([^;]+)(;)'  # NOSONAR
            modified_content, access_changes = replace_log_paths(
                modified_content, access_log_pattern, access_log_path, 'access_log'
            )
            changes.extend(access_changes)

        # 修改错误日志路径
        if error_log_path:
            # 处理主配置文件中的错误日志
            error_log_pattern = r'(error_log\s+)([^;]+)(;)'  # NOSONAR
            modified_content, error_changes = replace_log_paths(
                modified_content, error_log_pattern, error_log_path, 'error_log'
            )
            changes.extend(error_changes)

        return modified_content, changes

    except Exception as e:
        logger.error(f'修改日志路径失败: {e}')
        return body, changes

def replace_log_paths(body: str, pattern: str, new_path: str, log_type: str) -> Tuple[str, List[Dict]]:
    """替换日志路径"""
    changes = []

    try:
        # 安全验证：验证 new_path 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(new_path, allow_absolute=True)
        if not valid:
            logger.error(f"replace_log_paths: new_path 路径验证失败：{error_msg}")
            return body, changes

        def replacement(match):
            old_path = match.group(2).strip()
            change_info = {
                'type': log_type,
                'old_path': old_path,
                'new_path': new_path,
                'line_content': match.group(0)
            }
            changes.append(change_info)

            return match.group(1) + new_path + match.group(3)

        modified_content = re.sub(pattern, replacement, body)  # NOSONAR
        return modified_content, changes

    except Exception as e:
        logger.error(f'替换日志路径失败: {e}')
        return body, []

def verify_nginx_syntax(cfg_filepath: str) -> Dict:
    """检查 Nginx 配置语法"""
    try:
        # 安全验证：验证 cfg_filepath 路径参数（允许绝对路径）
        valid, error_msg = validate_path_param(cfg_filepath, allow_absolute=True)
        if not valid:
            logger.error(f"verify_nginx_syntax: cfg_filepath 路径验证失败：{error_msg}")
            return {
                'valid': False,
                'errors': [f'配置文件路径不安全：{error_msg}']
            }

        output = subprocess.run(['nginx', '-t', '-c', cfg_filepath], capture_output=True, text=True, timeout=30)

        errors = []
        if output.returncode != 0:
            error_output = output.stderr or output.stdout
            error_lines = error_output.split('\n')
            for line in error_lines:
                if 'emerg' in line.lower() or 'error' in line.lower():
                    errors.append(line.strip())

        return {
            'valid': output.returncode == 0,
            'errors': errors,
            'output': error_output if output.returncode != 0 else 'Syntax OK'
        }

    except subprocess.TimeoutExpired:
        return {
            'valid': False,
            'errors': ['语法检查超时'],
            'output': 'Timeout'
        }
    except Exception as e:
        return {
            'valid': False,
            'errors': [f'语法检查失败: {e}'],
            'output': str(e)
        }

def build_log_directories(access_log_path: Optional[str], error_log_path: Optional[str]):
    """创建日志目录"""
    try:
        paths_to_create = set()

        if access_log_path:
            # 安全验证：验证 access_log_path 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(access_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"build_log_directories: access_log_path 路径验证失败：{error_msg}")
                return

            access_dir = os.path.dirname(access_log_path)
            if access_dir:
                paths_to_create.add(access_dir)

        if error_log_path:
            # 安全验证：验证 error_log_path 路径参数（允许绝对路径）
            valid, error_msg = validate_path_param(error_log_path, allow_absolute=True)
            if not valid:
                logger.error(f"build_log_directories: error_log_path 路径验证失败：{error_msg}")
                return

            error_dir = os.path.dirname(error_log_path)
            if error_dir:
                paths_to_create.add(error_dir)

        for directory in paths_to_create:
            if directory and not os.path.exists(directory):
                Path(directory).mkdir(parents=True, exist_ok=True)
                # 设置适当的权限
                os.chmod(directory, 0o755)  # NOSONAR
                logger.info(f'创建日志目录：{directory}')

    except Exception as e:
        logger.error(f'创建日志目录失败: {e}')