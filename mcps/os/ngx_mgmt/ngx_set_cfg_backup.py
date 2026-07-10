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
logger = logging.getLogger('nginx_set_config_backup')

def save_nginx_configs(backup_path: Optional[str] = None) -> Dict:
    """
    备份当前所有Nginx配置文件（按时间戳命名、支持指定备份路径）

    参数:
        backup_path: 指定备份路径，如果为None则使用默认路径

    返回:
        Dict: 包含备份结果的字典
    """
    try:
        # 验证Nginx安装状态
        nginx_check = verify_nginx_installation()
        if not nginx_check['installed']:
            return {
                'success': False,
                'message': f"Nginx未安装: {nginx_check.get('suggestion', '请先安装Nginx')}",
                'backup_files': []
            }

        # 获取配置路径
        config_paths = fetch_config_paths()
        if config_paths['config_root'] == 'Unknown':
            return {
                'success': False,
                'message': '无法确定Nginx配置根目录',
                'backup_files': []
            }

        # 设置备份路径
        if not backup_path:
            backup_path = build_default_backup_path()

        # 创建备份目录
        backup_dir = build_backup_directory(backup_path)
        if not backup_dir:
            return {
                'success': False,
                'message': f'无法创建备份目录: {backup_path}',
                'backup_files': []
            }

        # 获取所有配置文件
        config_files = gather_all_config_files(config_paths)
        if not config_files:
            return {
                'success': False,
                'message': '未找到任何Nginx配置文件',
                'backup_files': []
            }

        # 执行备份
        backup_results = perform_backup(config_files, backup_dir)

        # 生成备份报告
        report = produce_backup_report(backup_results, backup_dir)

        # 验证备份完整性
        integrity_check = verify_backup_integrity(backup_results, config_files)

        return {
            'success': True,
            'message': f'Nginx配置文件备份完成',
            'backup_path': backup_dir,
            'backup_files': backup_results,
            'report': report,
            'integrity_check': integrity_check,
            'timestamp': datetime.datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f'备份Nginx配置失败: {e}')
        return {
            'success': False,
            'message': f'备份失败: {e}',
            'backup_files': []
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

def build_default_backup_path() -> str:
    """创建默认备份路径"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    default_path = f"/tmp/nginx_backup_{timestamp}"  # NOSONAR
    return default_path

def build_backup_directory(backup_path: str) -> Optional[str]:
    """创建备份目录"""
    try:
        Path(backup_path).mkdir(parents=True, exist_ok=True)

        # 创建子目录结构
        subdirs = ['configs', 'sites', 'modules', 'logs']
        for subdir in subdirs:
            subdir_path = os.path.join(backup_path, subdir)
            Path(subdir_path).mkdir(exist_ok=True)

        return backup_path

    except Exception as e:
        logger.error(f'创建备份目录失败: {e}')
        return None

def gather_all_config_files(config_paths: Dict) -> List[Dict]:
    """收集所有配置文件"""
    config_files = []

    try:
        # 主配置文件
        if os.path.exists(config_paths['main_config']):
            config_files.append({
                'type': 'main_config',
                'path': config_paths['main_config'],
                'description': 'Nginx主配置文件'
            })

        # 配置根目录下的所有.conf文件
        if config_paths['config_root'] != 'Unknown':
            config_root = config_paths['config_root']
            for root, dirs, files in os.walk(config_root):
                for file in files:
                    if file.endswith('.conf'):
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, config_root)
                        config_files.append({
                            'type': 'config_file',
                            'path': full_path,
                            'description': f'配置文件: {relative_path}'
                        })

        # 虚拟主机目录
        if config_paths['vhosts_dir'] != 'Unknown' and os.path.exists(config_paths['vhosts_dir']):
            for file in os.listdir(config_paths['vhosts_dir']):
                if file.endswith('.conf'):
                    full_path = os.path.join(config_paths['vhosts_dir'], file)
                    config_files.append({
                        'type': 'vhost_config',
                        'path': full_path,
                        'description': f'虚拟主机配置: {file}'
                    })

        # conf.d目录
        if config_paths['conf_d_dir'] != 'Unknown' and os.path.exists(config_paths['conf_d_dir']):
            for file in os.listdir(config_paths['conf_d_dir']):
                if file.endswith('.conf'):
                    full_path = os.path.join(config_paths['conf_d_dir'], file)
                    config_files.append({
                        'type': 'conf_d_config',
                        'path': full_path,
                        'description': f'conf.d配置: {file}'
                    })

        # 检查mime.types文件
        mime_types_path = os.path.join(config_paths['config_root'], 'mime.types')
        if os.path.exists(mime_types_path):
            config_files.append({
                'type': 'mime_types',
                'path': mime_types_path,
                'description': 'MIME类型配置文件'
            })

        # 检查fastcgi_params文件
        fastcgi_params_path = os.path.join(config_paths['config_root'], 'fastcgi_params')
        if os.path.exists(fastcgi_params_path):
            config_files.append({
                'type': 'fastcgi_params',
                'path': fastcgi_params_path,
                'description': 'FastCGI参数文件'
            })

        # 检查proxy_params文件
        proxy_params_path = os.path.join(config_paths['config_root'], 'proxy_params')
        if os.path.exists(proxy_params_path):
            config_files.append({
                'type': 'proxy_params',
                'path': proxy_params_path,
                'description': '代理参数文件'
            })

        return config_files

    except Exception as e:
        logger.error(f'收集配置文件失败: {e}')
        return []

def perform_backup(config_files: List[Dict], backup_dir: str) -> List[Dict]:
    """执行备份操作"""
    backup_results = []

    for config_file in config_files:
        try:
            source_path = config_file['path']
            if not os.path.exists(source_path):
                backup_results.append({
                    'success': False,
                    'file': source_path,
                    'backup_path': None,
                    'error': '源文件不存在',
                    'size': 0
                })
                continue

            # 生成备份文件名（保留目录结构）
            relative_path = os.path.relpath(source_path, '/')
            backup_filename = relative_path.replace('/', '_')
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{timestamp}_{backup_filename}"

            backup_path = os.path.join(backup_dir, 'configs', backup_filename)

            # 复制文件
            shutil.copy2(source_path, backup_path)

            # 获取文件信息
            file_stat = os.stat(source_path)

            backup_results.append({
                'success': True,
                'file': source_path,
                'backup_path': backup_path,
                'size': file_stat.st_size,
                'modified_time': datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'backup_time': datetime.datetime.now().isoformat()
            })

            logger.info(f'成功备份: {source_path} -> {backup_path}')

        except Exception as e:
            backup_results.append({
                'success': False,
                'file': config_file['path'],
                'backup_path': None,
                'error': str(e),
                'size': 0
            })
            logger.error(f'备份文件失败 {config_file["path"]}: {e}')

    return backup_results

def produce_backup_report(backup_results: List[Dict], backup_dir: str) -> Dict:
    """生成备份报告"""
    successful_backups = [r for r in backup_results if r['success']]
    failed_backups = [r for r in backup_results if not r['success']]

    total_size = sum(r.get('size', 0) for r in successful_backups)

    # 生成报告文件
    report_path = os.path.join(backup_dir, 'backup_report.json')

    report_data = {
        'backup_time': datetime.datetime.now().isoformat(),
        'backup_directory': backup_dir,
        'total_files': len(backup_results),
        'successful_backups': len(successful_backups),
        'failed_backups': len(failed_backups),
        'total_size_bytes': total_size,
        'total_size_human': render_file_size(total_size),
        'successful_files': [
            {
                'source': r['file'],
                'backup': r['backup_path'],
                'size': r['size']
            } for r in successful_backups
        ],
        'failed_files': [
            {
                'source': r['file'],
                'error': r.get('error', 'Unknown error')
            } for r in failed_backups
        ]
    }

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f'生成备份报告失败: {e}')

    return report_data