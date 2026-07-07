#!/usr/bin/env python3

import os
import re
import json
import time
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logger = logging.getLogger(__name__)


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
