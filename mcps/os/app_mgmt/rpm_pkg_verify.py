import logging
import os
import platform
import re
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_rpm_check.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_rpm_check')

def fetch_app_rpm_check(package_name=None, check_type=None):
    """
    采集RPM包完整性

    参数:
        package_name: 包名，如未指定则检查所有包
        check_type: 检查类型，可选值：
            - 'tamper': 检查是否被篡改
            - 'missing': 检查文件缺失
            - 'config': 检查配置文件变更
            - None: 检查所有类型

    返回:
        格式化的RPM包完整性检查结果字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== RPM包完整性检查 ===')

        # 检查系统是否支持RPM
        if not is_rpm_based_system():
            return "当前系统不是基于RPM的系统（如CentOS/RHEL/AlmaLinux）"

        # 根据参数执行检查
        if package_name:
            # 检查指定包
            if not is_package_installed(package_name):
                return f"RPM包 '{package_name}' 未安装"

            check_results = verify_package_integrity(package_name, check_type)
        else:
            # 检查所有包
            check_results = verify_all_packages_integrity(check_type)

        # 格式化结果
        if isinstance(check_results, dict):
            output.append(f"检查包: {check_results.get('package', 'Unknown')}")

            if 'tamper' in check_results:
                tamper_result = check_results['tamper']
                output.append(f"篡改检查: {'通过' if tamper_result['status'] else '失败'}")
                if not tamper_result['status']:
                    output.append(f"  失败原因: {tamper_result.get('reason', 'Unknown')}")

            if 'missing' in check_results:
                missing_result = check_results['missing']
                output.append(f"文件缺失检查: {'通过' if missing_result['status'] else '失败'}")
                if not missing_result['status']:
                    output.append(f"  缺失文件数: {len(missing_result.get('missing_files', []))}")
                    if missing_result.get('missing_files'):
                        output.append("  部分缺失文件:")
                        for file in missing_result['missing_files'][:5]:
                            output.append(f"    {file}")

            if 'config' in check_results:
                config_result = check_results['config']
                output.append(f"配置文件变更检查: {'通过' if config_result['status'] else '失败'}")
                if not config_result['status']:
                    output.append(f"  变更文件数: {len(config_result.get('changed_files', []))}")
                    if config_result.get('changed_files'):
                        output.append("  部分变更文件:")
                        for file in config_result['changed_files'][:5]:
                            output.append(f"    {file}")
        elif isinstance(check_results, list):
            output.append(f"检查包数量: {len(check_results)}")

            # 统计结果
            pass_count = 0
            fail_count = 0
            for pkg_result in check_results:
                if all(check['status'] for check in pkg_result.values() if isinstance(check, dict)):
                    pass_count += 1
                else:
                    fail_count += 1

            output.append(f"通过检查: {pass_count}个包")
            output.append(f"失败检查: {fail_count}个包")

            # 显示失败的包
            if fail_count > 0:
                output.append("\n失败的包（最多显示10个）:")
                failed_packages = [pkg for pkg in check_results if not all(check['status'] for check in pkg.values() if isinstance(check, dict))]
                for i, pkg in enumerate(failed_packages[:10]):
                    pkg_name = pkg.get('package', 'Unknown')
                    output.append(f"\n  {pkg_name}:")

                    if 'tamper' in pkg and not pkg['tamper']['status']:
                        output.append(f"    篡改检查: 失败")

                    if 'missing' in pkg and not pkg['missing']['status']:
                        missing_count = len(pkg['missing'].get('missing_files', []))
                        output.append(f"    文件缺失: {missing_count}个")

                    if 'config' in pkg and not pkg['config']['status']:
                        changed_count = len(pkg['config'].get('changed_files', []))
                        output.append(f"    配置变更: {changed_count}个")

    except Exception as e:
        logger.error(f'检查RPM包完整性失败: {e}')
        return f'检查RPM包完整性失败: {e}'

    output.append('=====================')
    return '\n'.join(output)
def is_rpm_based_system():
    """
    检查系统是否是基于RPM的系统

    返回:
        bool: 是否是基于RPM的系统
    """
    try:
        # 检查是否存在rpm命令
        output = subprocess.run(['which', 'rpm'], capture_output=True, text=True)
        if output.returncode == 0:
            return True

        # 检查系统发行版
        if os.path.exists('/etc/redhat-release'):
            return True

        # 检查系统类型
        distro = platform.platform().lower()
        return any(keyword in distro for keyword in ['centos', 'rhel', 'redhat', 'almalinux', 'fedora'])

    except Exception:
        return False
def is_package_installed(package_name):
    """
    检查RPM包是否已安装

    参数:
        package_name: 包名

    返回:
        bool: 是否已安装
    """
    try:
        output = subprocess.run(['rpm', '-q', package_name], capture_output=True, text=True)
        return output.returncode == 0

    except Exception:
        return False
def verify_package_integrity(package_name, check_type=None):
    """
    检查指定包的完整性

    参数:
        package_name: 包名
        check_type: 检查类型

    返回:
        检查结果字典
    """
    try:
        results = {
            'package': package_name
        }

        # 检查篡改
        if check_type in [None, 'tamper']:
            results['tamper'] = verify_package_tamper(package_name)

        # 检查文件缺失
        if check_type in [None, 'missing']:
            results['missing'] = verify_package_missing(package_name)

        # 检查配置文件变更
        if check_type in [None, 'config']:
            results['config'] = verify_package_config(package_name)

        return results

    except Exception as e:
        logger.error(f'检查包完整性失败 {package_name}: {e}')
        return {'package': package_name, 'error': str(e)}
def verify_all_packages_integrity(check_type=None):
    """
    检查所有包的完整性

    参数:
        check_type: 检查类型

    返回:
        检查结果列表
    """
    try:
        results = []

        # 获取所有已安装的包
        packages = fetch_all_installed_packages()

        # 检查每个包
        for package in packages[:10]:  # 只检查前10个包，避免性能问题
            package_result = verify_package_integrity(package, check_type)
            results.append(package_result)

        return results

    except Exception as e:
        logger.error(f'检查所有包完整性失败: {e}')
        return []
def verify_package_tamper(package_name):
    """
    检查包是否被篡改

    参数:
        package_name: 包名

    返回:
        检查结果字典
    """
    try:
        # 使用rpm -V检查包的完整性
        output = subprocess.run(['rpm', '-V', package_name], capture_output=True, text=True)

        if output.returncode == 0:
            return {
                'status': True,
                'reason': '无篡改'
            }
        else:
            # 解析错误输出
            output = output.stdout.strip()
            if output:
                return {
                    'status': False,
                    'reason': output[:200]  # 只取前200字符
                }
            else:
                return {
                    'status': False,
                    'reason': '检查失败'
                }

    except Exception as e:
        return {
            'status': False,
            'reason': str(e)
        }
def verify_package_missing(package_name):
    """
    检查包文件是否缺失

    参数:
        package_name: 包名

    返回:
        检查结果字典
    """
    try:
        # 获取包中的所有文件
        files = fetch_package_files(package_name)
        missing_files = []

        # 检查每个文件是否存在
        for file in files:
            if not os.path.exists(file):
                missing_files.append(file)

        return {
            'status': len(missing_files) == 0,
            'missing_files': missing_files
        }

    except Exception as e:
        return {
            'status': False,
            'missing_files': [],
            'reason': str(e)
        }
