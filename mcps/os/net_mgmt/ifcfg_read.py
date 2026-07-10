# 网卡配置文件采集工具

def fetch_net_ifcfg(interface=None):
    """
    采集网卡配置文件
    """
    return '=== 网卡配置文件 ===\nifcfg配置文件: /etc/sysconfig/network-scripts/ifcfg-*\ninterfaces配置文件: /etc/network/interfaces\n====================='

# 工具配置
TOOL_CONFIG = {
    "name": "fetch_net_ifcfg",
    "function": fetch_net_ifcfg,
    "description": "采集网卡配置文件",
    "parameters": {
        "type": "object",
        "properties": {
            "interface": {
                "type": "string",
                "description": "网络接口名称"
            }
        },
        "required": []
    }
}
