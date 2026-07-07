#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nginx 缓存监控工具
用于获取Nginx缓存的命中率、命中/失效/过期数、缓存占用空间、缓存配置规则等信息
"""

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_nginx_cache_stats():
    """获取Nginx缓存统计信息"""
    cache_stats = {
        'hit_ratio': 'N/A',
        'hits': 'N/A',
        'misses': 'N/A',
        'expired': 'N/A',
        'stale': 'N/A',
        'updating': 'N/A',
        'revalidated': 'N/A',
        'scarce': 'N/A',
        'cache_size': 'N/A',
        'cache_max_size': 'N/A',
        'cache_keys_zone': 'N/A',
        'cache_path': 'N/A',
        'cache_levels': 'N/A',
        'cache_inactive': 'N/A',
        'cache_config': {}
    }
    
    try:
        # 获取Nginx配置信息
        cache_config = fetch_nginx_cache_config()
        cache_stats['cache_config'] = cache_config
        
        # 获取缓存状态信息
        status_stats = fetch_cache_status_stats()
        cache_stats.update(status_stats)
        
        # 获取缓存占用空间
        disk_stats = fetch_cache_disk_usage()
        cache_stats.update(disk_stats)
        
        return cache_stats
        
    except Exception as e:
        logger.error(f'获取缓存统计失败: {e}')
        return cache_stats


def fetch_nginx_cache_config():
    """获取Nginx缓存配置信息"""
    settings = {
        'proxy_cache_path': [],
        'fastcgi_cache_path': [],
        'proxy_cache': [],
        'fastcgi_cache': [],
        'cache_zones': {}
    }
    
    try:
        # 获取Nginx配置文件内容
        config_content = fetch_nginx_config_content()
        
        if not config_content:
            return settings
        
        # 解析 proxy_cache_path 指令
        proxy_cache_paths = re.findall(  # NOSONAR
            r'proxy_cache_path\s+(\S+)\s+keys_zone=([^:]+):(\d+)(?:\s+inactive=([^;\s]+))?(?:\s+max_size=([^;\s]+))?(?:\s+use_temp_path=([^;\s]+))?(?:\s+levels=([^;\s]+))?',
            config_content, re.IGNORECASE  # NOSONAR
        )
        
        for path_info in proxy_cache_paths:
            cache_info = {
                'path': path_info[0],
                'zone_name': path_info[1],
                'zone_size': f"{path_info[2]}m",
                'inactive': path_info[3] if path_info[3] else '10m',
                'max_size': path_info[4] if path_info[4] else 'N/A',
                'use_temp_path': path_info[5] if path_info[5] else 'on',
                'levels': path_info[6] if path_info[6] else '1:2',
                'type': 'proxy'
            }
            settings['proxy_cache_path'].append(cache_info)
            settings['cache_zones'][cache_info['zone_name']] = cache_info
        
        # 解析 fastcgi_cache_path 指令
        fastcgi_cache_paths = re.findall(  # NOSONAR
            r'fastcgi_cache_path\s+(\S+)\s+keys_zone=([^:]+):(\d+)(?:\s+inactive=([^;\s]+))?(?:\s+max_size=([^;\s]+))?(?:\s+use_temp_path=([^;\s]+))?(?:\s+levels=([^;\s]+))?',
            config_content, re.IGNORECASE  # NOSONAR
        )
        
        for path_info in fastcgi_cache_paths:
            cache_info = {
                'path': path_info[0],
                'zone_name': path_info[1],
                'zone_size': f"{path_info[2]}m",
                'inactive': path_info[3] if path_info[3] else '10m',
                'max_size': path_info[4] if path_info[4] else 'N/A',
                'use_temp_path': path_info[5] if path_info[5] else 'on',
                'levels': path_info[6] if path_info[6] else '1:2',
                'type': 'fastcgi'
            }
            settings['fastcgi_cache_path'].append(cache_info)
            settings['cache_zones'][cache_info['zone_name']] = cache_info
        
        # 解析 proxy_cache 指令
        proxy_caches = re.findall(  # NOSONAR
            r'proxy_cache\s+([^;\s]+)',
            config_content, re.IGNORECASE  # NOSONAR
        )
        settings['proxy_cache'] = sorted(set(proxy_caches))
        
        # 解析 fastcgi_cache 指令
        fastcgi_caches = re.findall(  # NOSONAR
            r'fastcgi_cache\s+([^;\s]+)',
            config_content, re.IGNORECASE  # NOSONAR
        )
        settings['fastcgi_cache'] = sorted(set(fastcgi_caches))
        
        return settings
        
    except Exception as e:
        logger.error(f'获取缓存配置失败: {e}')
        return settings


def fetch_nginx_config_content():
    """获取Nginx配置文件内容"""
    try:
        # 使用 nginx -T 命令获取完整配置
        output = subprocess.run(
            ['nginx', '-T'], 
            capture_output=True, 
            text=True, 
            stderr=subprocess.STDOUT,
            timeout=10
        )
        
        if output.returncode in [0, 1]:
            return output.stdout
        else:
            logger.error(f'nginx -T 命令执行失败: {output.stderr}')
            return ""
            
    except subprocess.TimeoutExpired:
        logger.error('nginx -T 命令执行超时')
        return ""
    except FileNotFoundError:
        logger.error('nginx 命令未找到')
        return ""
    except Exception as e:
        logger.error(f'获取Nginx配置失败: {e}')
        return ""


def fetch_cache_status_stats():
    """获取缓存状态统计"""
    stats = {
        'hit_ratio': 'N/A',
        'hits': 'N/A',
        'misses': 'N/A',
        'expired': 'N/A',
        'stale': 'N/A',
        'updating': 'N/A',
        'revalidated': 'N/A',
        'scarce': 'N/A'
    }
    
    try:
        # 尝试从 stub_status 模块获取缓存统计
        stub_info = fetch_nginx_stub_status_info()
        if stub_info and 'location' in stub_info:
            stub_stats = fetch_stub_status_stats(stub_info['location'])
            if stub_stats:
                # 从 stub_status 获取基本连接信息
                stats.update({
                    'active_connections': stub_stats.get('active_connections', 'N/A'),
                    'total_requests': stub_stats.get('total_requests', 'N/A')
                })
        
        # 尝试从 Nginx Plus API 获取缓存统计
        plus_stats = fetch_nginx_plus_cache_stats()
        if plus_stats:
            stats.update(plus_stats)
        
        # 计算命中率（如果有足够的数据）
        if stats['hits'] != 'N/A' and stats['misses'] != 'N/A':
            total = stats['hits'] + stats['misses']
            if total > 0:
                stats['hit_ratio'] = f"{(stats['hits'] / total) * 100:.2f}%"
        
        return stats
        
    except Exception as e:
        logger.error(f'获取缓存状态统计失败: {e}')
        return stats


def fetch_nginx_stub_status_info():
    """获取Nginx stub_status 模块信息"""
    try:
        # 查找包含 stub_status 的配置
        config_content = fetch_nginx_config_content()
        
        # 匹配 stub_status 配置
        stub_match = re.search(  # NOSONAR
            r'location\s+([^/{}\s]+)\s*\{[^}]*stub_status\s+on',
            config_content, re.IGNORECASE | re.DOTALL  # NOSONAR
        )
        
        if stub_match:
            return {
                'location': stub_match.group(1),
                'full_path': f"http://localhost{stub_match.group(1)}"  # NOSONAR
            }
        
        return None
        
    except Exception as e:
        logger.error(f'获取 stub_status 信息失败: {e}')
        return None


def fetch_stub_status_stats(status_url):
    """从 stub_status 页面获取统计信息"""
    stats = {}
    try:
        response = requests.get(status_url, timeout=5)
        if response.status_code == 200:
            body = response.text.strip()
            
            # 解析 stub_status 输出
            # Active connections: 291
            active_match = re.search(r'Active connections:\s*(\d+)', body)  # NOSONAR
            if active_match:
                stats['active_connections'] = int(active_match.group(1))
            
            # server accepts handled requests
            # 16630948 16630948 31070465
            server_match = re.search(  # NOSONAR
                r'server\s+accepts\s+handled\s+requests\s*\n\s*(\d+)\s+(\d+)\s+(\d+)',  # NOSONAR 
                body  # NOSONAR
                )  # NOSONAR
            if server_match:
                stats['total_connections'] = int(server_match.group(1))
                stats['total_handshakes'] = int(server_match.group(2))
                stats['total_requests'] = int(server_match.group(3))
            
            # Reading: 6 Writing: 179 Waiting: 106
            reading_match = re.search(r'Reading:\s*(\d+)', body)  # NOSONAR
            writing_match = re.search(r'Writing:\s*(\d+)', body)  # NOSONAR
            waiting_match = re.search(r'Waiting:\s*(\d+)', body)  # NOSONAR
            
            if reading_match:
                stats['reading_connections'] = int(reading_match.group(1))
            if writing_match:
                stats['writing_connections'] = int(writing_match.group(1))
            if waiting_match:
                stats['waiting_connections'] = int(waiting_match.group(1))
                
    except Exception as e:
        logger.error(f'获取 stub_status 统计失败: {e}')
    
    return stats


def fetch_nginx_plus_cache_stats():
    """获取 Nginx Plus 缓存统计（如果可用）"""
    stats = {}
    try:
        # 尝试访问 Nginx Plus API
        api_urls = [
            "http://localhost/api/3/http/caches",  # NOSONAR
            "http://localhost/api/2/http/caches",  # NOSONAR
            "http://127.0.0.1/api/3/http/caches",  # NOSONAR
            "http://127.0.0.1/api/2/http/caches"  # NOSONAR
        ]
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, timeout=5)
                if response.status_code == 200:
                    cache_data = response.json()
                    
                    # 汇总所有缓存区的统计
                    total_hits = 0
                    total_misses = 0
                    total_expired = 0
                    total_stale = 0
                    total_updating = 0
                    total_revalidated = 0
                    total_scarce = 0
                    
                    for cache_name, cache_info in cache_data.items():
                        if 'hit' in cache_info:
                            total_hits += cache_info['hit']
                        if 'miss' in cache_info:
                            total_misses += cache_info['miss']
                        if 'expired' in cache_info:
                            total_expired += cache_info['expired']
                        if 'stale' in cache_info:
                            total_stale += cache_info['stale']
                        if 'updating' in cache_info:
                            total_updating += cache_info['updating']
                        if 'revalidated' in cache_info:
                            total_revalidated += cache_info['revalidated']
                        if 'scarce' in cache_info:
                            total_scarce += cache_info['scarce']
                    
                    stats = {
                        'hits': total_hits,
                        'misses': total_misses,
                        'expired': total_expired,
                        'stale': total_stale,
                        'updating': total_updating,
                        'revalidated': total_revalidated,
                        'scarce': total_scarce
                    }
                    break
                    
            except requests.exceptions.RequestException:
                continue
            except Exception:
                continue
                
    except Exception as e:
        logger.error(f'获取 Nginx Plus 缓存统计失败: {e}')
    
    return stats


def fetch_cache_disk_usage():
    """获取缓存磁盘使用情况"""
    stats = {
        'cache_size': 'N/A',
        'cache_max_size': 'N/A',
        'cache_path': 'N/A',
        'cache_levels': 'N/A',
        'cache_keys_zone': 'N/A',
        'cache_inactive': 'N/A'
    }
    
    try:
        # 获取缓存配置
        cache_config = fetch_nginx_cache_config()
        
        if cache_config['proxy_cache_path']:
            # 使用第一个缓存路径
            cache_info = cache_config['proxy_cache_path'][0]
            cache_path = cache_info['path']
            
            # 计算缓存目录大小
            cache_size = fetch_directory_size(cache_path)
            
            stats.update({
                'cache_path': cache_path,
                'cache_size': render_size(cache_size),
                'cache_max_size': cache_info['max_size'] if cache_info['max_size'] != 'N/A' else 'unlimited',
                'cache_levels': cache_info['levels'],
                'cache_keys_zone': f"{cache_info['zone_name']}:{cache_info['zone_size']}",
                'cache_inactive': cache_info['inactive']
            })
        
        elif cache_config['fastcgi_cache_path']:
            # 使用第一个 FastCGI 缓存路径
            cache_info = cache_config['fastcgi_cache_path'][0]
            cache_path = cache_info['path']
            
            # 计算缓存目录大小
            cache_size = fetch_directory_size(cache_path)
            
            stats.update({
                'cache_path': cache_path,
                'cache_size': render_size(cache_size),
                'cache_max_size': cache_info['max_size'] if cache_info['max_size'] != 'N/A' else 'unlimited',
                'cache_levels': cache_info['levels'],
                'cache_keys_zone': f"{cache_info['zone_name']}:{cache_info['zone_size']}",
                'cache_inactive': cache_info['inactive']
            })
        
        return stats
        
    except Exception as e:
        logger.error(f'获取缓存磁盘使用情况失败: {e}')
        return stats


def fetch_directory_size(directory):
    """获取目录大小（字节）"""
    try:
        if not os.path.exists(directory):
            return 0
        
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    continue
        
        return total_size
        
    except Exception as e:
        logger.error(f'计算目录大小失败: {e}')
        return 0


def render_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    
    while size_bytes >= 1024 and unit_index < len(units) - 1:
        size_bytes /= 1024
        unit_index += 1
    
    return f"{size_bytes:.2f} {units[unit_index]}"


def examine_cache_health(cache_stats):
    """分析缓存健康状态"""
    analysis = {
        'cache_efficiency': 'N/A',
        'cache_status': 'N/A',
        'recommendations': []
    }
    
    try:
        # 检查命中率
        hit_ratio = cache_stats.get('hit_ratio', 'N/A')
        if hit_ratio != 'N/A' and '%' in hit_ratio:
            ratio_value = float(hit_ratio.replace('%', ''))
            
            if ratio_value >= 80:
                analysis['cache_efficiency'] = "优秀"
                analysis['cache_status'] = "🟢 缓存运行良好"
            elif ratio_value >= 60:
                analysis['cache_efficiency'] = "良好"
                analysis['cache_status'] = "🟢 缓存效率良好"
            elif ratio_value >= 40:
                analysis['cache_efficiency'] = "一般"
                analysis['cache_status'] = "🟡 缓存效率一般"
            else:
                analysis['cache_efficiency'] = "较差"
                analysis['cache_status'] = "🔴 缓存效率较低"
            
            # 提供建议
            if ratio_value < 60:
                analysis['recommendations'].append("建议优化缓存策略，提高命中率")
            
            if ratio_value < 40:
                analysis['recommendations'].append("考虑调整缓存过期时间或缓存大小")
        
        # 检查缓存大小
        cache_size = cache_stats.get('cache_size', 'N/A')
        cache_max_size = cache_stats.get('cache_max_size', 'N/A')
        
        if cache_size != 'N/A' and cache_max_size != 'N/A' and cache_max_size != 'unlimited':
            # 解析大小
            current_size = analyze_size(cache_size)
            max_size = analyze_size(cache_max_size)
            
            if current_size > 0 and max_size > 0:
                usage_percentage = (current_size / max_size) * 100
                
                if usage_percentage >= 90:
                    analysis['recommendations'].append("⚠️  缓存空间即将用尽，建议清理或扩容")
                elif usage_percentage >= 80:
                    analysis['recommendations'].append("🟡 缓存空间使用率较高，建议监控")
        
        return analysis
        
    except Exception as e:
        logger.error(f'分析缓存健康状态失败: {e}')
        return analysis


def analyze_size(size_str):
    """解析大小字符串为字节数"""
    try:
        if size_str == 'N/A' or size_str == 'unlimited':
            return 0
        
        # 移除空格并转换为大写
        size_str = size_str.strip().upper()
        
        # 定义单位转换因子
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
        
        # 提取数值和单位
        match = re.match(r'^(\d+(?:\.\d+)?)\s*([A-Z]+)$', size_str)  # NOSONAR
        if not match:
            raise ValueError(f"无法解析大小字符串: {size_str}")
        
        val, unit = match.groups()
        val = float(val)
        
        if unit not in units:
            raise ValueError(f"未知单位: {unit}")
        
        return val * units[unit]
        
    except Exception as e:
        logger.error(f'解析大小字符串失败: {e}')
        return 0


TOOL_CONFIG = {
    "name": "fetch_nginx_cache_stats",
    "description": "获取Nginx缓存统计信息，包括命中率、缓存大小、缓存配置等",
    "function": fetch_nginx_cache_stats,
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
