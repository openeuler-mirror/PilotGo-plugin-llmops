#!/usr/bin/env python3

import subprocess
import psutil
import os
import time
import logging
from datetime import datetime
import signal

from mcp_tools.ngx_mgmt.ngx_helpers import get_nginx_process_info

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('nginx_process_stop')


def examine_stop_recommendations():
    """
    分析并推荐停止策略

    Returns:
        dict: 推荐策略
    """
    try:
        proc_info = get_nginx_process_info()
        if proc_info["status"] == "已停止":
            return {"recommendation": "无需停止", "reason": "Nginx服务已经停止"}

        connection_count = fetch_active_connections_count()
        current_time = datetime.now().strftime("%H:%M")

        recommendations = []

        # 根据连接数和时间推荐策略
        if connection_count == 0:
            recommendations.append({
                "type": "immediate",
                "priority": "high",
                "reason": "当前无活动连接，可立即停止"
            })
        elif connection_count < 10:
            recommendations.append({
                "type": "graceful",
                "priority": "medium",
                "reason": f"活动连接较少({connection_count}个)，建议平滑停止"
            })
        else:
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": f"活动连接较多({connection_count}个)，必须平滑停止以保持服务连续性"
            })

        # 根据时间推荐
        hour = datetime.now().hour
        if 2 <= hour <= 5:  # 凌晨时段
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": "当前为业务低峰期，适合进行平滑停止"
            })
        elif 9 <= hour <= 18:  # 工作时间
            recommendations.append({
                "type": "graceful",
                "priority": "high",
                "reason": "当前为业务高峰期，必须使用平滑停止"
            })

        # 选择优先级最高的推荐
        priority_map = {"high": 3, "medium": 2, "low": 1}
        best_recommendation = max(recommendations, key=lambda x: priority_map[x["priority"]])

        return {
            "current_status": {
                "nginx_running": proc_info["status"] == "运行中",
                "active_connections": connection_count,
                "current_time": current_time
            },
            "recommendations": recommendations,
            "best_recommendation": best_recommendation
        }

    except Exception as e:
        logger.error(f"分析停止推荐失败: {e}")
        return {"error": f"分析失败: {e}"}
