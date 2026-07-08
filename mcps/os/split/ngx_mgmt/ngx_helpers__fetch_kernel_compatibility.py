#!/usr/bin/env python3

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
