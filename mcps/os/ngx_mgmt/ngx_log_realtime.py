import subprocess
import platform
import os
import re
import logging
import time
import threading
import select
from datetime import datetime
from mcp_tools.cmd_safety_guard import validate_identifier_param, validate_path_param
from .utils import (
    check_nginx_installation
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_log_real_time')

def tail_nginx_logs(log_type='access', filter_keyword=None, lines=50, follow=True, duration=60):
    """
    实时采集 Nginx日志（类似 tail -f），支持按日志类型/关键词过滤的 MCP 工具
    
    参数:
        log_type: 日志类型 ('access', 'error', 'both')
        filter_keyword: 关键词过滤（可选）
        lines: 显示初始行数
        follow: 是否实时跟踪
        duration: 跟踪持续时间（秒）
    
    返回:
        格式化的实时日志信息字符串
    """
    try:
        # 安全验证：验证 log_type 参数
        valid_log_types = ['access', 'error', 'both']
        if log_type not in valid_log_types:
            logger.error(f"log_type 参数不合法：{log_type}")
            return '{"status": "error", "message": f"log_type 必须是 {valid_log_types} 之一"}'
        
        # 安全验证：验证 filter_keyword 参数（如果提供）
        if filter_keyword is not None:
            valid, error_msg = validate_identifier_param(filter_keyword)
            if not valid:
                logger.error(f"filter_keyword 验证失败：{error_msg}")
                return '{"status": "error", "message": "关键词过滤参数不安全：' + error_msg + '"}'
        
        # 安全验证：验证 lines 参数
        if not isinstance(lines, int) or lines <= 0 or lines > 10000:
            logger.error(f"lines 参数不合法：{lines}")
            return '{"status": "error", "message": "lines 必须是 1-10000 之间的整数"}'
        
        # 安全验证：验证 duration 参数
        if not isinstance(duration, (int, float)) or duration <= 0 or duration > 3600:
            logger.error(f"duration 参数不合法：{duration}")
            return '{"status": "error", "message": "duration 必须是 1-3600 秒之间的数值"}'
        
        output = []
        output.append('=== Nginx 实时日志采集 ===')
        
        # 检查Nginx是否安装
        nginx_check = check_nginx_installation()
        if not nginx_check['installed']:
            output.append(f"Nginx状态: 未安装")
            output.append(f"建议: {nginx_check['suggestion']}")
            output.append('============================')
            return '\n'.join(output)
        
        output.append(f"Nginx状态: 已安装")
        output.append(f"日志类型: {log_type}")
        if filter_keyword:
            output.append(f"关键词过滤: '{filter_keyword}'")
        output.append(f"初始行数: {lines}")
        output.append(f"实时跟踪: {'开启' if follow else '关闭'}")
        if follow:
            output.append(f"跟踪时长: {duration}秒")
        
        # 获取日志文件路径
        log_files = fetch_nginx_log_files(log_type)
        if not log_files:
            output.append(f"错误: 未找到{log_type}日志文件")
            output.append('============================')
            return '\n'.join(output)
        
        output.append(f"\n=== 日志文件信息 ===")
        for log_file in log_files:
            output.append(f"文件: {log_file['path']}")
            output.append(f"类型: {log_file['type']}")
            output.append(f"大小: {log_file['size']}")
            output.append(f"修改时间: {log_file['mtime']}")
        
        # 显示初始日志内容
        output.append(f"\n=== 初始日志内容（最近{lines}行） ===")
        initial_content = fetch_initial_log_content(log_files, lines, filter_keyword)
        if initial_content:
            output.extend(initial_content)
        else:
            output.append("无匹配的日志内容")
        
        # 实时跟踪日志
        if follow:
            output.append(f"\n=== 开始实时跟踪（持续{duration}秒） ===")
            output.append("按 Ctrl+C 可提前终止跟踪")
            output.append("------------------------")
            
            # 创建实时跟踪线程
            real_time_content = []
            stop_event = threading.Event()
            
            def real_time_tail():
                try:
                    # 使用 tail -f 命令实时跟踪
                    tail_processes = []
                    for log_file in log_files:
                        # 安全验证：验证日志文件路径
                        log_path = log_file['path']
                        valid, error_msg = validate_path_param(log_path)
                        if not valid:
                            logger.error(f"日志文件路径验证失败：{error_msg}")
                            real_time_content.append(f"错误：日志文件路径不安全 - {log_path}")
                            continue
                        
                        if filter_keyword:
                            # 不使用 shell=True，而是使用 subprocess.Popen 的 stdin/stdout 管道
                            # 先启动 tail 进程
                            tail_cmd = ['tail', '-f', log_path]
                            tail_process = subprocess.Popen(
                                tail_cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True,
                                bufsize=1
                            )
                            # 再启动 grep 进程
                            grep_cmd = ['grep', filter_keyword]
                            grep_process = subprocess.Popen(
                                grep_cmd,
                                stdin=tail_process.stdout,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1
                            )
                            # 关闭 tail 的 stdout 以避免死锁
                            tail_process.stdout.close()
                            process = grep_process
                        else:
                            process = subprocess.Popen(
                                ['tail', '-f', log_path], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True,
                                bufsize=1
                            )
                        tail_processes.append(process)
                    
                    start_time = time.time()
                    
                    while not stop_event.is_set() and (time.time() - start_time) < duration:
                        # 检查所有进程的输出
                        for process in tail_processes:
                            if select.select([process.stdout], [], [], 0.1)[0]:
                                line = process.stdout.readline()
                                if line:
                                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    real_time_content.append(f"[{timestamp}] {line.strip()}")
                        
                        # 短暂休眠避免CPU占用过高
                        time.sleep(0.1)
                    
                    # 终止进程
                    for process in tail_processes:
                        try:
                            process.terminate()
                            process.wait(timeout=1)
                        except Exception:
                            process.kill()
                            
                except Exception as e:
                    logger.error(f'实时跟踪失败: {e}')
                    real_time_content.append(f"实时跟踪错误: {e}")
            
            # 启动实时跟踪线程
            tail_thread = threading.Thread(target=real_time_tail)
            tail_thread.start()
            
            # 等待跟踪完成或超时
            tail_thread.join(timeout=duration + 5)
            stop_event.set()
            
            # 添加实时跟踪结果
            if real_time_content:
                output.extend(real_time_content)
            else:
                output.append("实时跟踪期间未发现新的日志内容")
        
        output.append('\n============================')
        return '\n'.join(output)
        
    except Exception as e:
        logger.error(f'实时采集Nginx日志失败: {e}')
        return f'实时采集Nginx日志失败: {e}'

def fetch_nginx_log_files(log_type):
    """
    获取 Nginx日志文件路径
    
    参数:
        log_type: 日志类型 ('access', 'error', 'both')
    
    返回:
        list: 日志文件信息列表
    """
    try:
        # 安全验证：验证 log_type 参数
        valid_log_types = ['access', 'error', 'both']
        if log_type not in valid_log_types:
            logger.error(f"fetch_nginx_log_files: log_type 参数不合法：{log_type}")
            return []
        
        log_files = []
        
        # 获取Nginx配置信息
        cfg_state = fetch_nginx_config_info()
        if cfg_state['config_file'] == 'Unknown':
            # 如果无法获取配置，使用默认路径
            return fetch_default_log_files(log_type)
        
        # 解析配置文件获取日志路径
        log_config = analyze_nginx_log_config(cfg_state['config_file'])
        
        # 根据日志类型选择文件
        if log_type in ['access', 'both']:
            for access_log in log_config['access_logs']:
                if access_log['path'] not in ['stderr', 'syslog'] and os.path.exists(access_log['path']):
                    log_files.append({
                        'path': access_log['path'],
                        'type': 'access',
                        'size': access_log.get('size', 'Unknown'),
                        'mtime': fetch_file_mtime(access_log['path'])
                    })
        
        if log_type in ['error', 'both']:
            for error_log in log_config['error_logs']:
                if error_log['path'] not in ['stderr', 'syslog'] and os.path.exists(error_log['path']):
                    log_files.append({
                        'path': error_log['path'],
                        'type': 'error',
                        'size': error_log.get('size', 'Unknown'),
                        'mtime': fetch_file_mtime(error_log['path'])
                    })
        
        # 如果没有找到日志文件，使用默认路径
        if not log_files:
            log_files = fetch_default_log_files(log_type)
        
        return log_files
        
    except Exception as e:
        logger.error(f'获取Nginx日志文件失败: {e}')
        return fetch_default_log_files(log_type)

def fetch_default_log_files(log_type):
    """
    获取默认的 Nginx日志文件路径
    
    参数:
        log_type: 日志类型
    
    返回:
        list: 默认日志文件列表
    """
    try:
        # 安全验证：验证 log_type 参数
        valid_log_types = ['access', 'error', 'both']
        if log_type not in valid_log_types:
            logger.error(f"fetch_default_log_files: log_type 参数不合法：{log_type}")
            return []
        
        log_files = []
        common_log_dirs = ['/var/log/nginx', '/usr/local/nginx/logs', '/var/log']
        
        for log_dir in common_log_dirs:
            if os.path.exists(log_dir):
                # 访问日志文件
                if log_type in ['access', 'both']:
                    access_logs = [
                        os.path.join(log_dir, 'access.log'),
                        os.path.join(log_dir, 'access_log'),
                        os.path.join(log_dir, 'nginx-access.log')
                    ]
                    for log_path in access_logs:
                        if os.path.exists(log_path):
                            log_files.append({
                                'path': log_path,
                                'type': 'access',
                                'size': render_file_size(os.path.getsize(log_path)),
                                'mtime': fetch_file_mtime(log_path)
                            })
                            break
                
                # 错误日志文件
                if log_type in ['error', 'both']:
                    error_logs = [
                        os.path.join(log_dir, 'error.log'),
                        os.path.join(log_dir, 'error_log'),
                        os.path.join(log_dir, 'nginx-error.log')
                    ]
                    for log_path in error_logs:
                        if os.path.exists(log_path):
                            log_files.append({
                                'path': log_path,
                                'type': 'error',
                                'size': render_file_size(os.path.getsize(log_path)),
                                'mtime': fetch_file_mtime(log_path)
                            })
                            break
                
                # 如果找到了文件，不再检查其他目录
                if log_files:
                    break
        
        return log_files
        
    except Exception as e:
        logger.error(f'获取默认日志文件失败: {e}')
        return []

def fetch_initial_log_content(log_files, lines, filter_keyword):
    """
    获取初始日志内容
    
    参数:
        log_files: 日志文件列表
        lines: 显示行数
        filter_keyword: 关键词过滤
    
    返回:
        list: 日志内容列表
    """
    try:
        # 安全验证：验证 lines 参数
        if not isinstance(lines, int) or lines <= 0 or lines > 10000:
            logger.error(f"fetch_initial_log_content: lines 参数不合法：{lines}")
            lines = 50  # 使用默认值
        
        # 安全验证：验证 filter_keyword 参数（如果提供）
        if filter_keyword is not None:
            valid, error_msg = validate_identifier_param(filter_keyword)
            if not valid:
                logger.error(f"fetch_initial_log_content: filter_keyword 验证失败：{error_msg}")
                return [f"关键词过滤参数不安全：{error_msg}"]
        
        body = []
        
        for log_file in log_files:
            # 使用tail命令获取最后几行
            cmd = ['tail', f'-n{lines}', log_file['path']]
            
            if filter_keyword:
                # 使用grep过滤
                output = subprocess.run(['grep', filter_keyword, log_file['path']], capture_output=True, text=True)
                if output.returncode == 0:
                    lines_content = output.stdout.strip().split('\n')[-lines:]
                    for line in lines_content:
                        if line.strip():
                            body.append(f"[{log_file['type']}] {line.strip()}")
            else:
                # 直接获取最后几行
                output = subprocess.run(cmd, capture_output=True, text=True)
                if output.returncode == 0:
                    for line in output.stdout.strip().split('\n'):
                        if line.strip():
                            body.append(f"[{log_file['type']}] {line.strip()}")
        
        return body
        
    except Exception as e:
        logger.error(f'获取初始日志内容失败: {e}')
        return [f"获取日志内容失败: {e}"]

def analyze_nginx_log_config(config_file):
    """
    解析 Nginx 配置文件获取日志配置（从 nginx-log-path.py 复制）
    
    参数:
        config_file: 配置文件路径
    
    返回:
        dict: 日志配置信息
    """
    try:
        # 安全验证：验证 config_file 路径参数
        valid, error_msg = validate_path_param(config_file)
        if not valid:
            logger.error(f"analyze_nginx_log_config: config_file 路径验证失败：{error_msg}")
            return {
                'access_logs': [],
                'error_logs': []
            }
        
        log_info = {
            'access_logs': [],
            'error_logs': []
        }
        
        if not os.path.exists(config_file):
            return log_info
        
        with open(config_file, 'r', encoding='utf-8') as f:
            body = f.read()
        
        # 解析访问日志配置
        access_log_matches = re.findall(r'access_log\s+([^;]+);', body)  # NOSONAR
        for match in access_log_matches:
            access_log_info = analyze_access_log_directive(match.strip())
            if access_log_info:
                log_info['access_logs'].append(access_log_info)
        
        # 解析错误日志配置
        error_log_matches = re.findall(r'error_log\s+([^;]+);', body)  # NOSONAR
        for match in error_log_matches:
            error_log_info = analyze_error_log_directive(match.strip())
            if error_log_info:
                log_info['error_logs'].append(error_log_info)
        
        return log_info
        
    except Exception as e:
        logger.error(f'解析Nginx日志配置失败: {e}')
        return {
            'access_logs': [],
            'error_logs': []
        }

def analyze_access_log_directive(directive):
    """
    解析access_log指令（从nginx-log-path.py复制）
    """
    try:
        parts = directive.split()
        if not parts:
            return None
        
        log_info = {
            'path': 'Unknown',
            'size': 'Unknown'
        }
        
        log_info['path'] = parts[0]
        
        if os.path.exists(log_info['path']):
            try:
                size = os.path.getsize(log_info['path'])
                log_info['size'] = render_file_size(size)
            except Exception:
                log_info['size'] = '无法获取大小'
        
        return log_info
        
    except Exception as e:
        logger.error(f'解析access_log指令失败: {e}')
        return None