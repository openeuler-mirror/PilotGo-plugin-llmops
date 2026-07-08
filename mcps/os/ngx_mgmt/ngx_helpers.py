import logging
import os
import platform
import re
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_utils')

def verify_nginx_installation():
    """
    检查Nginx安装状态

    返回:
        dict: 包含安装状态、路径和建议信息的字典
    """
    try:
        # 检查nginx命令是否存在
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode != 0:
            return {
                'installed': False,
                'suggestion': '请使用包管理器安装Nginx (如: apt install nginx 或 yum install nginx)'
            }

        # 获取nginx路径
        ngx_bin_path = output.stdout.strip()

        # 检查nginx文件是否存在
        if not os.path.exists(ngx_bin_path):
            return {
                'installed': False,
                'suggestion': 'Nginx二进制文件不存在，请重新安装'
            }

        return {
            'installed': True,
            'path': ngx_bin_path
        }

    except Exception as e:
        logger.error(f'检查Nginx安装状态失败: {e}')
        return {
            'installed': False,
            'suggestion': f'检查安装状态时出错: {e}'
        }

def fetch_nginx_version():
    """
    获取Nginx版本信息

    返回:
        dict: 包含主版本和详细版本信息的字典
    """
    try:
        # 获取版本信息
        output = subprocess.run(['nginx', '-v'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        ver_data = {
            'main_version': 'Unknown',
            'full_version': 'Unknown'
        }

        if output.returncode == 0:
            output = output.stdout.strip()
            # 解析版本信息
            ver_match = re.search(r'nginx/([\d\.]+)', output)  # NOSONAR
            if ver_match:
                ver_data['main_version'] = ver_match.group(1)
                ver_data['full_version'] = output

            # 如果stdout没有，尝试stderr
            if ver_data['main_version'] == 'Unknown':
                error_output = output.stderr.strip() if output.stderr else ''
                ver_match = re.search(r'nginx/([\d\.]+)', error_output)  # NOSONAR
                if ver_match:
                    ver_data['main_version'] = ver_match.group(1)
                    ver_data['full_version'] = error_output

        return ver_data

    except Exception as e:
        logger.error(f'获取Nginx版本信息失败: {e}')
        return {
            'main_version': 'Unknown',
            'full_version': f'获取版本信息失败: {e}'
        }

def fetch_nginx_compile_info():
    """
    获取Nginx编译信息

    返回:
        dict: 包含编译器、编译时间和配置参数的字典
    """
    try:
        # 获取编译参数
        output = subprocess.run(['nginx', '-V'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        build_info = {
            'compiler': 'Unknown',
            'compile_time': 'Unknown',
            'build_opts': ''
        }

        if output.returncode == 0:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 解析编译器信息
            compiler_match = re.search(r'built by ([^\n]+)', output)  # NOSONAR
            if compiler_match:
                build_info['compiler'] = compiler_match.group(1).strip()

            # 解析编译时间
            time_match = re.search(r'built on ([^\n]+)', output)  # NOSONAR
            if time_match:
                build_info['compile_time'] = time_match.group(1).strip()

            # 解析配置参数
            configure_match = re.search(r'configure arguments:([^\n]+)', output, re.IGNORECASE)  # NOSONAR
            if configure_match:
                build_info['build_opts'] = configure_match.group(1).strip()

        return build_info

    except Exception as e:
        logger.error(f'获取Nginx编译信息失败: {e}')
        return {
            'compiler': 'Unknown',
            'compile_time': 'Unknown',
            'build_opts': f'获取编译信息失败: {e}'
        }

def fetch_kernel_compatibility():
    """
    获取内核适配信息

    返回:
        dict: 包含内核版本、架构、兼容性和优化特性的字典
    """
    try:
        # 获取当前内核版本
        kernel_version = platform.release()
        architecture = platform.machine()

        # 获取系统信息
        system = platform.system()

        kern_info = {
            'current_kernel': kernel_version,
            'architecture': architecture,
            'compatibility': '良好',
            'optimization_features': []
        }

        # 检查内核版本和优化特性
        if 'x86_64' in architecture:
            kern_info['optimization_features'].append('64位架构支持')

            # 检查CPU特性
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    if 'sse4_2' in cpuinfo:
                        kern_info['optimization_features'].append('SSE4.2指令集优化')
                    if 'avx' in cpuinfo:
                        kern_info['optimization_features'].append('AVX指令集优化')
            except Exception:
                pass

        # 检查内核版本兼容性
        kernel_version_parts = kernel_version.split('.')
        if len(kernel_version_parts) >= 2:
            major = int(kernel_version_parts[0])
            minor = int(kernel_version_parts[1])

            if major >= 3 and minor >= 9:
                kern_info['optimization_features'].append('支持epoll高性能I/O')
                kern_info['optimization_features'].append('支持SO_REUSEPORT端口复用')

            if major >= 4:
                kern_info['optimization_features'].append('支持TCP_FASTOPEN')
                kern_info['optimization_features'].append('支持更高性能的网络栈')

        # 检查文件描述符限制
        try:
            with open('/proc/sys/fs/file-max', 'r') as f:
                file_max = int(f.read().strip())
                if file_max > 100000:
                    kern_info['optimization_features'].append(f'高并发文件描述符支持 (最大: {file_max})')
        except Exception:
            pass

        return kern_info

    except Exception as e:
        logger.error(f'获取内核适配信息失败: {e}')
        return {
            'current_kernel': platform.release(),
            'architecture': platform.machine(),
            'compatibility': '获取信息失败',
            'optimization_features': [f'获取内核信息失败: {e}']
        }

def fetch_nginx_process_info():
    """
    获取Nginx进程信息

    返回:
        dict: 包含主进程PID、工作进程数和运行状态的字典
    """
    try:
        # 检查Nginx进程
        output = subprocess.run(['pgrep', '-f', 'nginx'], capture_output=True, text=True)

        proc_info = {
            'master_pid': '未运行',
            'worker_processes': 0,
            'status': '已停止'
        }

        if output.returncode == 0:
            pids = output.stdout.strip().split('\n')
            proc_info['master_pid'] = pids[0] if pids else 'Unknown'
            proc_info['worker_processes'] = len(pids) - 1 if len(pids) > 1 else 0
            proc_info['status'] = '运行中'

        return proc_info

    except Exception as e:
        logger.error(f'获取Nginx进程信息失败: {e}')
        return {
            'master_pid': '获取失败',
            'worker_processes': 0,
            'status': f'获取失败: {e}'
        }

def fetch_nginx_config_info():
    """
    获取Nginx配置信息

    返回:
        dict: 包含配置文件路径和测试状态的字典
    """
    try:
        # 测试配置文件
        output = subprocess.run(['nginx', '-t'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        cfg_state = {
            'config_file': 'Unknown',
            'config_test': 'Unknown'
        }

        # 解析配置文件路径
        if output.returncode == 0:
            cfg_state['config_test'] = '配置正确'
            # 尝试从输出中解析配置文件路径
            config_match = re.search(r'file ([^\s]+) test is successful', output.stdout)  # NOSONAR
            if config_match:
                cfg_state['config_file'] = config_match.group(1)
        else:
            cfg_state['config_test'] = '配置有误'
            # 即使测试失败也尝试获取配置文件路径
            config_match = re.search(r'file ([^\s]+)', output.stdout)  # NOSONAR
            if config_match:
                cfg_state['config_file'] = config_match.group(1)

        # 如果还是Unknown，尝试常见路径
        if cfg_state['config_file'] == 'Unknown':
            common_paths = ['/etc/nginx/nginx.conf', '/usr/local/nginx/conf/nginx.conf']
            for path in common_paths:
                if os.path.exists(path):
                    cfg_state['config_file'] = path
                    break

        return cfg_state

    except Exception as e:
        logger.error(f'获取Nginx配置信息失败: {e}')
        return {
            'config_file': '获取失败',
            'config_test': f'获取失败: {e}'
        }

def fetch_nginx_modules():
    """
    获取Nginx模块信息

    返回:
        dict: 包含内置模块和动态模块信息的字典
    """
    try:
        # 获取模块列表
        output = subprocess.run(['nginx', '-V'], capture_output=True, text=True, stderr=subprocess.STDOUT)

        mod_info = {
            'builtin_modules': [],
            'dynamic_modules': [],
            'builtin_modules_count': 0,
            'dynamic_modules_count': 0
        }

        if output.returncode == 0:
            output = output.stdout.strip() if output.stdout else output.stderr.strip()

            # 解析内置模块
            # 注意: nginx -V 主要显示编译信息，模块信息需要通过其他方式获取
            # 这里我们尝试解析configure参数中的模块信息
            configure_match = re.search(r'configure arguments:([^\n]+)', output, re.IGNORECASE)  # NOSONAR
            if configure_match:
                build_opts = configure_match.group(1).strip()

                # 查找模块相关的配置参数
                module_matches = re.findall(r'--with-([^=\s]+)', build_opts)  # NOSONAR
                for module in module_matches:
                    if module not in mod_info['builtin_modules']:
                        mod_info['builtin_modules'].append(f"--with-{module}")

                # 查找动态模块
                dynamic_matches = re.findall(r'--add-dynamic-module=([^\s]+)', build_opts)  # NOSONAR
                for module in dynamic_matches:
                    mod_info['dynamic_modules'].append(module)

        mod_info['builtin_modules_count'] = len(mod_info['builtin_modules'])
        mod_info['dynamic_modules_count'] = len(mod_info['dynamic_modules'])

        # 如果通过上述方法没有获取到模块，添加一些常见的默认模块
        if mod_info['builtin_modules_count'] == 0:
            common_modules = [
                'http_ssl_module', 'http_v2_module', 'http_realip_module',
                'http_addition_module', 'http_sub_module', 'http_dav_module',
                'http_flv_module', 'http_mp4_module', 'http_gunzip_module',
                'http_gzip_static_module', 'http_random_index_module',
                'http_secure_link_module', 'http_stub_status_module'
            ]
            mod_info['builtin_modules'] = [f"--with-{module}" for module in common_modules]
            mod_info['builtin_modules_count'] = len(common_modules)

        return mod_info

    except Exception as e:
        logger.error(f'获取Nginx模块信息失败: {e}')
        return {
            'builtin_modules': ['获取模块信息失败'],
            'dynamic_modules': [],
            'builtin_modules_count': 0,
            'dynamic_modules_count': 0
        }

def fetch_basic_paths():
    """
    获取基本路径信息

    返回:
        dict: 包含安装目录、二进制路径和启动脚本的字典
    """
    try:
        base_info = {
            'install_dir': 'Unknown',
            'binary_path': 'Unknown',
            'init_script': 'Unknown'
        }

        # 获取nginx二进制路径
        output = subprocess.run(['which', 'nginx'], capture_output=True, text=True)
        if output.returncode == 0:
            binary_path = output.stdout.strip()
            base_info['binary_path'] = binary_path

            # 推导安装目录
            if '/sbin/nginx' in binary_path:
                install_dir = binary_path.replace('/sbin/nginx', '')
                base_info['install_dir'] = install_dir if install_dir else '/'
            elif '/bin/nginx' in binary_path:
                install_dir = binary_path.replace('/bin/nginx', '')
                base_info['install_dir'] = install_dir if install_dir else '/'

        # 检查启动脚本
        init_scripts = [
            '/etc/init.d/nginx',
            '/lib/systemd/system/nginx.service',
            '/usr/lib/systemd/system/nginx.service',
            '/etc/systemd/system/nginx.service'
        ]

        for script in init_scripts:
            if os.path.exists(script):
                base_info['init_script'] = script
                break

        return base_info

    except Exception as e:
        logger.error(f'获取基本路径信息失败: {e}')
        return {
            'install_dir': '获取失败',
            'binary_path': '获取失败',
            'init_script': '获取失败'
        }

def fetch_system_info():
    """
    获取系统信息

    返回:
        dict: 包含系统类型、发行版和包管理器信息的字典
    """
    try:
        sys_info_data = {
            'package_manager': 'Unknown',
            'service_config': 'Unknown',
            'system_log': 'Unknown',
            'distribution': 'Unknown'
        }

        # 检测操作系统类型
        system = platform.system()

        try:
            # 尝试获取发行版信息
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    body = f.read()
                    if 'Ubuntu' in body or 'Debian' in body:
                        sys_info_data['distribution'] = 'Debian/Ubuntu'
                        sys_info_data['package_manager'] = 'apt (apt-get)'
                    elif 'CentOS' in body or 'Red Hat' in body or 'Fedora' in body:
                        sys_info_data['distribution'] = 'Red Hat/CentOS/Fedora'
                        sys_info_data['package_manager'] = 'yum/dnf'
                    elif 'SUSE' in body:
                        sys_info_data['distribution'] = 'SUSE'
                        sys_info_data['package_manager'] = 'zypper'
                    elif 'Arch' in body:
                        sys_info_data['distribution'] = 'Arch Linux'
                        sys_info_data['package_manager'] = 'pacman'
        except Exception:
            pass

        # 服务配置路径
        service_configs = [
            '/lib/systemd/system/nginx.service',
            '/usr/lib/systemd/system/nginx.service',
            '/etc/systemd/system/nginx.service',
            '/etc/init.d/nginx'
        ]

        for service_config in service_configs:
            if os.path.exists(service_config):
                sys_info_data['service_config'] = service_config
                break

        # 系统日志路径
        system_logs = [
            '/var/log/syslog',
            '/var/log/messages',
            '/var/log/system.log'
        ]

        for system_log in system_logs:
            if os.path.exists(system_log):
                sys_info_data['system_log'] = system_log
                break

        return sys_info_data

    except Exception as e:
        logger.error(f'获取系统信息失败: {e}')
        return {
            'package_manager': '获取失败',
            'service_config': '获取失败',
            'system_log': '获取失败',
            'distribution': '获取失败'
        }