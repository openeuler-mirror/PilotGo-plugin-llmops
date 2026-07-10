import logging
import os
import platform
import subprocess

LOG_DIR = os.path.join(os.path.expanduser("~"), ".software_applications_logs")
os.makedirs(LOG_DIR, mode=0o700, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app_update_available.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE
)
logger = logging.getLogger('app_update_available')

def fetch_app_update_available(package_manager=None, check_security=True):
    """
    采集可更新软件（系统可更新的包/版本差异/更新大小/安全更新标识）

    参数:
        package_manager: 包管理器类型，如未指定则自动检测
        check_security: 是否检查安全更新

    返回:
        格式化的可更新软件信息字符串
    """
    try:
        # 基本信息
        output = []
        output.append('=== 可更新软件信息 ===')

        # 自动检测包管理器
        if not package_manager:
            package_manager = spot_package_manager()
            if not package_manager:
                output.append('错误: 未检测到支持的包管理器')
                output.append('支持的包管理器: apt, yum, dnf, zypper')
                output.append('=====================')
                return '\n'.join(output)

        package_manager = package_manager.lower()

        # 根据包管理器获取可更新软件
        if package_manager == 'apt':
            updates = fetch_apt_updates(check_security)
        elif package_manager == 'yum':
            updates = fetch_yum_updates(check_security)
        elif package_manager == 'dnf':
            updates = fetch_dnf_updates(check_security)
        elif package_manager == 'zypper':
            updates = fetch_zypper_updates(check_security)
        else:
            output.append(f'错误: 不支持的包管理器: {package_manager}')
            output.append('支持的包管理器: apt, yum, dnf, zypper')
            output.append('=====================')
            return '\n'.join(output)

        # 格式化结果
        if not updates:
            output.append('当前系统没有可更新的软件包')
        else:
            # 分类更新
            security_updates = []
            normal_updates = []

            for update in updates:
                if update.get('is_security', False):
                    security_updates.append(update)
                else:
                    normal_updates.append(update)

            # 显示安全更新
            if security_updates:
                output.append(f"安全更新 ({len(security_updates)}):")
                for update in security_updates[:10]:  # 最多显示10个
                    output.append(f"  - {update['name']}")
                    output.append(f"    当前版本: {update['current_version']}")
                    output.append(f"    可用版本: {update['available_version']}")
                    if 'size' in update:
                        output.append(f"    更新大小: {update['size']}")

                if len(security_updates) > 10:
                    output.append(f"  ... 还有 {len(security_updates) - 10} 个安全更新未显示 ...")

            # 显示普通更新
            if normal_updates:
                output.append(f"\n普通更新 ({len(normal_updates)}):")
                for update in normal_updates[:10]:  # 最多显示10个
                    output.append(f"  - {update['name']}")
                    output.append(f"    当前版本: {update['current_version']}")
                    output.append(f"    可用版本: {update['available_version']}")
                    if 'size' in update:
                        output.append(f"    更新大小: {update['size']}")

                if len(normal_updates) > 10:
                    output.append(f"  ... 还有 {len(normal_updates) - 10} 个普通更新未显示 ...")

            # 显示总计
            total_updates = len(security_updates) + len(normal_updates)
            output.append(f"\n总计可更新软件包: {total_updates}")
            if security_updates:
                output.append(f"其中安全更新: {len(security_updates)}")

        # 显示系统信息
        sys_info_data = fetch_system_info()
        output.append(f"\n系统信息: {sys_info_data}")
        output.append(f"包管理器: {package_manager}")

        output.append('=====================')
        return '\n'.join(output)

    except Exception as e:
        logger.error(f'获取可更新软件信息失败: {e}')
        return f'获取可更新软件信息失败: {e}'
