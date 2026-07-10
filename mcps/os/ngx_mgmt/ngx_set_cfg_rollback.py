from pathlib import Path
from typing import Dict, List, Optional, Tuple
import datetime
import json
import logging
import os
import re
import shutil
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_set_config_rollback')

def revert_nginx_config(backup_path: str, target_version: Optional[str] = None) -> Dict:
    """
    回滚配置到指定备份版本（自动校验语法、重载配置）

    参数:
        backup_path: 备份文件或备份目录路径
        target_version: 目标版本标识（时间戳或版本号），如果为None则使用最新版本

    返回:
        Dict: 包含回滚结果的字典
    """
    try:
        # 验证Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'rollback_files': []
            }

        # 获取当前配置路径
        config_paths = fetch_config_paths()
        if config_paths['config_root'] == 'Unknown':
            return {
                'success': False,
                'message': '无法确定Nginx配置根目录',
                'rollback_files': []
            }

        # 验证备份路径
        if not os.path.exists(backup_path):
            return {
                'success': False,
                'message': f'备份路径不存在: {backup_path}',
                'rollback_files': []
            }

        # 查找目标备份版本
        target_backup = locate_target_backup(backup_path, target_version)
        if not target_backup:
            return {
                'success': False,
                'message': f'未找到指定的备份版本: {target_version}' if target_version else '未找到有效的备份文件',
                'rollback_files': []
            }

        # 备份当前配置（创建回滚点）
        current_backup = save_current_config(config_paths)

        # 执行回滚操作
        rollback_results = perform_rollback(target_backup, config_paths)

        # 语法校验
        syntax_check = certify_nginx_syntax()

        # 如果语法校验失败，自动回滚到之前的状态
        if not syntax_check['success']:
            logger.warning('回滚后语法校验失败，自动恢复原配置')
            recover_from_backup(current_backup, config_paths)
            return {
                'success': False,
                'message': f'回滚后语法校验失败: {syntax_check["error"]}，已自动恢复原配置',
                'rollback_files': rollback_results,
                'syntax_check': syntax_check,
                'original_backup': current_backup
            }

        # 重载配置
        reload_result = reload_nginx_config()

        # 生成回滚报告
        report = produce_rollback_report(rollback_results, target_backup, syntax_check, reload_result)

        return {
            'success': True,
            'message': 'Nginx配置回滚完成',
            'target_version': target_backup.get('version', 'Unknown'),
            'rollback_files': rollback_results,
            'syntax_check': syntax_check,
            'reload_result': reload_result,
            'report': report,
            'original_backup': current_backup,
            'timestamp': datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f'回滚Nginx配置失败: {e}')
        return {
            'success': False,
            'message': f'回滚失败: {e}',
            'rollback_files': []
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

def fetch_config_paths() -> Dict:
    """获取Nginx配置路径信息"""
    try:
        cfg_state = {
            'config_root': 'Unknown',
            'main_config': 'Unknown',
            'vhosts_dir': 'Unknown',
            'conf_d_dir': 'Unknown'
        }

        # 常见配置路径
        common_config_paths = [
            '/etc/nginx/nginx.conf',
            '/usr/local/nginx/conf/nginx.conf',
            '/usr/local/etc/nginx/nginx.conf',
            '/opt/nginx/conf/nginx.conf'
        ]

        # 检查nginx -t输出获取配置文件路径
        try:
            output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)
            if output.returncode == 0 or output.returncode == 1:
                output = output.stdout.strip()
                config_match = re.search(r'file ([^\s]+) test', output)  # NOSONAR
                if config_match:
                    config_file = config_match.group(1)
                    cfg_state['main_config'] = config_file
                    cfg_state['config_root'] = os.path.dirname(config_file)
        except Exception:
            pass

        # 如果通过nginx -t没有获取到，检查常见路径
        if cfg_state['main_config'] == 'Unknown':
            for config_path in common_config_paths:
                if os.path.exists(config_path):
                    cfg_state['main_config'] = config_path
                    cfg_state['config_root'] = os.path.dirname(config_path)
                    break

        # 如果找到了配置根目录，检查子目录
        if cfg_state['config_root'] != 'Unknown':
            config_root = cfg_state['config_root']

            # 检查sites-enabled/sites-available (Debian/Ubuntu风格)
            if os.path.exists(os.path.join(config_root, 'sites-enabled')):
                cfg_state['vhosts_dir'] = os.path.join(config_root, 'sites-enabled')
            elif os.path.exists(os.path.join(config_root, 'conf.d')):
                cfg_state['vhosts_dir'] = os.path.join(config_root, 'conf.d')

            # 检查conf.d目录
            if os.path.exists(os.path.join(config_root, 'conf.d')):
                cfg_state['conf_d_dir'] = os.path.join(config_root, 'conf.d')

        return cfg_state

    except Exception as e:
        logger.error(f'获取配置路径信息失败: {e}')
        return {
            'config_root': '获取失败',
            'main_config': '获取失败',
            'vhosts_dir': '获取失败',
            'conf_d_dir': '获取失败'
        }

def locate_target_backup(backup_path: str, target_version: Optional[str] = None) -> Optional[Dict]:
    """查找目标备份版本"""
    try:
        backup_files = []

        # 如果是目录，查找所有备份文件
        if os.path.isdir(backup_path):
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    if file.endswith('.conf') or 'backup' in file.lower():
                        full_path = os.path.join(root, file)
                        backup_info = examine_backup_file(full_path)
                        if backup_info:
                            backup_files.append(backup_info)

        # 如果是文件，直接分析
        elif os.path.isfile(backup_path):
            backup_info = examine_backup_file(backup_path)
            if backup_info:
                backup_files.append(backup_info)

        # 按时间戳排序（最新的在前）
        backup_files.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        # 如果没有指定版本，使用最新版本
        if not target_version and backup_files:
            return backup_files[0]

        # 查找指定版本
        for backup in backup_files:
            if target_version and (
                target_version in backup.get('filename', '') or
                target_version == backup.get('version', '') or
                target_version == backup.get('timestamp_str', '')
            ):
                return backup

        return None

    except Exception as e:
        logger.error(f'查找目标备份失败: {e}')
        return None

def examine_backup_file(file_path: str) -> Optional[Dict]:
    """分析备份文件信息"""
    try:
        filename = os.path.basename(file_path)
        file_stat = os.stat(file_path)

        # 提取时间戳
        timestamp_match = re.search(r'(\d{8}_\d{6})', filename)  # NOSONAR
        timestamp_str = timestamp_match.group(1) if timestamp_match else None

        # 解析时间戳
        timestamp = 0
        if timestamp_str:
            try:
                dt = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                timestamp = dt.timestamp()
            except Exception:
                pass

        # 如果没有时间戳，使用文件修改时间
        if timestamp == 0:
            timestamp = file_stat.st_mtime
            timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')

        # 推断原始文件路径
        original_path = infer_original_path(filename, file_path)

        return {
            'path': file_path,
            'filename': filename,
            'timestamp': timestamp,
            'timestamp_str': timestamp_str,
            'version': timestamp_str,
            'size': file_stat.st_size,
            'original_path': original_path,
            'modified_time': datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }

    except Exception as e:
        logger.error(f'分析备份文件失败: {e}')
        return None

def infer_original_path(filename: str, backup_path: str) -> str:
    """推断原始文件路径"""
    try:
        # 从文件名中提取原始路径信息
        # 移除时间戳部分
        clean_name = re.sub(r'\d{8}_\d{6}_', '', filename)  # NOSONAR
        clean_name = re.sub(r'\.backup$', '', clean_name)  # NOSONAR

        # 常见配置路径映射
        path_mappings = {
            'nginx_conf': '/etc/nginx/nginx.conf',
            'etc_nginx_nginx_conf': '/etc/nginx/nginx.conf',
            'sites_available': '/etc/nginx/sites-available/',
            'conf_d': '/etc/nginx/conf.d/',
            'mime_types': '/etc/nginx/mime.types',
            'fastcgi_params': '/etc/nginx/fastcgi_params'
        }

        # 尝试匹配已知路径
        for key, path in path_mappings.items():
            if key in clean_name:
                if path.endswith('/'):
                    # 如果是目录，需要进一步处理
                    return path + clean_name.replace(key + '_', '')
                return path

        # 默认使用常见配置路径
        config_paths = fetch_config_paths()
        if config_paths['config_root'] != 'Unknown':
            return os.path.join(config_paths['config_root'], clean_name)

        return f'/etc/nginx/{clean_name}'

    except Exception as e:
        logger.error(f'推断原始路径失败: {e}')
        return '/etc/nginx/unknown.conf'

def save_current_config(config_paths: Dict) -> Dict:
    """备份当前配置（创建回滚点）"""
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"/tmp/nginx_rollback_backup_{timestamp}"  # NOSONAR

        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        backup_files = []

        # 备份主配置文件
        if os.path.exists(config_paths['main_config']):
            backup_path = os.path.join(backup_dir, f"current_{os.path.basename(config_paths['main_config'])}")
            shutil.copy2(config_paths['main_config'], backup_path)
            backup_files.append({
                'original': config_paths['main_config'],
                'backup': backup_path
            })

        # 备份虚拟主机配置
        if config_paths['vhosts_dir'] != 'Unknown' and os.path.exists(config_paths['vhosts_dir']):
            vhost_backup_dir = os.path.join(backup_dir, 'vhosts')
            Path(vhost_backup_dir).mkdir(exist_ok=True)

            for file in os.listdir(config_paths['vhosts_dir']):
                if file.endswith('.conf'):
                    original_path = os.path.join(config_paths['vhosts_dir'], file)
                    backup_path = os.path.join(vhost_backup_dir, f"current_{file}")
                    shutil.copy2(original_path, backup_path)
                    backup_files.append({
                        'original': original_path,
                        'backup': backup_path
                    })

        # 备份conf.d配置
        if config_paths['conf_d_dir'] != 'Unknown' and os.path.exists(config_paths['conf_d_dir']):
            confd_backup_dir = os.path.join(backup_dir, 'conf.d')
            Path(confd_backup_dir).mkdir(exist_ok=True)

            for file in os.listdir(config_paths['conf_d_dir']):
                if file.endswith('.conf'):
                    original_path = os.path.join(config_paths['conf_d_dir'], file)
                    backup_path = os.path.join(confd_backup_dir, f"current_{file}")
                    shutil.copy2(original_path, backup_path)
                    backup_files.append({
                        'original': original_path,
                        'backup': backup_path
                    })

        return {
            'backup_dir': backup_dir,
            'backup_files': backup_files,
            'timestamp': timestamp
        }

    except Exception as e:
        logger.error(f'备份当前配置失败: {e}')
        return {
            'backup_dir': None,
            'backup_files': [],
            'timestamp': datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        }

def perform_rollback(target_backup: Dict, config_paths: Dict) -> List[Dict]:
    """执行回滚操作"""
    rollback_results = []

    try:
        backup_file = target_backup['path']
        original_path = target_backup['original_path']

        # 确保目标目录存在
        target_dir = os.path.dirname(original_path)
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        # 备份当前文件（如果存在）
        if os.path.exists(original_path):
            backup_current = f"{original_path}.rollback_backup"
            shutil.copy2(original_path, backup_current)

        # 执行回滚（复制备份文件到目标位置）
        shutil.copy2(backup_file, original_path)

        # 验证文件是否成功复制
        if os.path.exists(original_path):
            file_stat = os.stat(original_path)
            rollback_results.append({
                'success': True,
                'backup_file': backup_file,
                'target_file': original_path,
                'size': file_stat.st_size,
                'rollback_time': datetime.datetime.now().isoformat()
            })
            logger.info(f'成功回滚: {backup_file} -> {original_path}')
        else:
            rollback_results.append({
                'success': False,
                'backup_file': backup_file,
                'target_file': original_path,
                'error': '回滚后目标文件不存在'
            })
            logger.error(f'回滚失败: 目标文件不存在 {original_path}')

    except Exception as e:
        rollback_results.append({
            'success': False,
            'backup_file': target_backup['path'],
            'target_file': target_backup['original_path'],
            'error': str(e)
        })
        logger.error(f'执行回滚失败: {e}')

    return rollback_results

def certify_nginx_syntax() -> Dict:
    """验证Nginx语法"""
    try:
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True)

        if output.returncode == 0:
            return {
                'success': True,
                'message': '语法校验通过',
                'output': output.stdout.strip()
            }
        else:
            error_output = output.stderr if output.stderr else output.stdout
            return {
                'success': False,
                'error': '语法校验失败',
                'output': error_output.strip()
            }

    except Exception as e:
        logger.error(f'语法校验失败: {e}')
        return {
            'success': False,
            'error': f'语法校验过程出错: {e}'
        }

def reload_nginx_config() -> Dict:
    """重载Nginx配置"""
    try:
        # 尝试使用systemctl重载（如果可用）
        output = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)

        if output.returncode == 0:
            return {
                'success': True,
                'method': 'systemctl',
                'message': '使用systemctl重载成功',
                'output': output.stdout.strip()
            }

        # 如果systemctl失败，尝试使用nginx -s reload
        output = subprocess.run(['nginx', '-s', 'reload'], capture_output=True, text=True)

        if output.returncode == 0:
            return {
                'success': True,
                'method': 'nginx -s reload',
                'message': '使用nginx -s reload重载成功',
                'output': output.stdout.strip()
            }

        # 如果都失败，返回错误
        return {
            'success': False,
            'error': '重载配置失败',
            'output': output.stderr.strip() if output.stderr else output.stdout.strip()
        }

    except Exception as e:
        logger.error(f'重载配置失败: {e}')
        return {
            'success': False,
            'error': f'重载过程出错: {e}'
        }