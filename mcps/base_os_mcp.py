import os
import asyncio
import importlib.util
import logging
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# 导入验证中间件模块
# 该模块提供工具白名单验证和参数验证功能
from mcp_tools.security import SecurityMiddleware

# 配置日志系统
# 记录工具调用、执行结果和错误信息，用于审计和调试
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('base_os_mcp')

# 创建 MCP 服务器实例
# 服务器名称为 "kylin-ops-mcp"，用于标识这个服务
server = Server("kylin-ops-mcp")

# 工具白名单
# 只有在这个集合中的工具才能被执行
# 这是一种安全机制，防止执行未授权的工具
TOOL_WHITELIST = {
    # "agent_name",

    # 硬件资源类工具
    "hardware_resources/hw_cpu_basic",      # CPU 基础信息
    "hardware_resources/hw_mem_physical",  # 物理内存信息
    "hardware_resources/hw_mem_virtual",  # 虚拟内存信息
    "hardware_resources/hw_disk_physical", # 物理磁盘信息

    # 系统基础类工具
    "system_basics/sys_arch_info",        # 系统架构信息
    "system_basics/sys_dist_info",        # 发行版信息
    "system_basics/sys_host_info",        # 主机信息
    "system_basics/sys_kernel_info",      # 内核信息
    "system_basics/sys_os_release",       # OS 发布信息
    "system_basics/sys_timezone",         # 时区信息
    "system_basics/sys_uptime_info",      # 运行时间信息

    # 存储文件系统类工具
    "storage_filesystems/fs_mount_info",   # 挂载信息
    "storage_filesystems/fs_df_detail",    # 磁盘空间详情
    "storage_filesystems/fs_du_detail",    # 目录使用详情

    # 软件应用类工具
    "software_applications/app_rpm_list", # RPM 包列表
    "software_applications/app_rpm_info",  # RPM 包信息
    "software_applications/app_rpm_check", # RPM 包检查
    "software_applications/app_yum_repo",  # YUM 源信息

    # 用户权限类工具
    "user_permissions/user_info",         # 用户信息
    "user_permissions/user_all",         # 所有用户信息
    "user_permissions/user_group_info",  # 用户组信息
    "user_permissions/user_group_all",   # 所有用户组信息
    "user_permissions/user_login_info",  # 用户登录信息

    # 定时任务类工具
    "cron_task/cron_task_list",          # 定时任务列表
}


def load_tools_from_directory(directory: str, whitelist: set) -> list:
    """
    从指定目录加载工具模块
    
    该函数会遍历目录下的所有 Python 文件，
    检查每个模块是否有 TOOL_CONFIG 属性，
    如果有且在白名单中，则加载该工具。
    
    参数:
        directory (str): 工具模块所在目录路径
        whitelist (set): 允许加载的工具名称集合
    
    返回:
        list: 工具配置列表，每个元素是一个包含 name、function、description、parameters 的字典
    
    处理流程:
        1. 检查目录是否存在
        2. 递归遍历目录下所有 .py 文件
        3. 检查文件名是否在白名单中
        4. 使用 importlib 动态导入模块
        5. 提取 TOOL_CONFIG 配置
    """
    tools = []
    
    # 检查目录是否存在
    if not os.path.exists(directory):
        return tools
    
    # 递归遍历目录
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # 只处理 Python 文件，排除以 _ 或 . 开头的文件
            if filename.endswith('.py') and not filename.startswith('_') and not filename.startswith('.'):
                # 移除 .py 后缀作为模块名
                module_name = filename[:-3]
                file_path = os.path.join(root, filename)
                
                # 计算相对于目录的路径，作为工具键名
                relative_path = os.path.relpath(file_path, directory)
                tool_key = relative_path.replace('.py', '')
                
                # 检查是否在白名单中
                if tool_key not in whitelist:
                    continue
                
                # 动态导入模块
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 检查模块是否有 TOOL_CONFIG 属性
                        if hasattr(module, 'TOOL_CONFIG'):
                            tools.append(module.TOOL_CONFIG)
                except Exception as e:
                    print(f"加载工具 {file_path} 失败: {e}")
    
    return tools


# 定义工具目录路径
# 工具模块位于 mcp_tools 子目录中
tools_directory = os.path.join(os.path.dirname(__file__), 'mcp_tools')

# 加载工具模块
# 从指定目录加载所有在白名单中的工具
loaded_tools = load_tools_from_directory(tools_directory, TOOL_WHITELIST)

# 创建验证中间件实例
# 该中间件会在工具执行前验证:
# 1. 工具是否在白名单中
# 2. 参数是否符合 schema 定义
# 3. 是否包含危险字符
security = SecurityMiddleware(
    whitelist=TOOL_WHITELIST,
    loaded_tools=loaded_tools,
    enable_rate_limit=False,
    enable_audit=True,
    audit_config={
        "max_records": 10000,
        "log_file": None
    }
)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    列出所有可用的工具
    
    这是 MCP 协议的必备方法，
    返回服务器支持的所有工具列表及其参数 schema。
    LLM 会根据这个列表决定可以调用哪些工具。
    
    返回:
        list[Tool]: MCP Tool 对象列表，每个包含:
            - name: 工具名称
            - description: 工具描述
            - inputSchema: 参数 JSON Schema
    """
    tools = []
    for tool_config in loaded_tools:
        tool = Tool(
            name=tool_config["name"],
            description=tool_config["description"],
            inputSchema=tool_config["parameters"]
        )
        tools.append(tool)
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    调用指定的工具
    
    这是 MCP 协议的核心方法，
    负责执行用户请求的工具并返回结果。
    在执行前会先通过验证中间件进行安全检查。
    
    参数:
        name (str): 要调用的工具名称
        arguments (dict): 传递给工具的参数
    
    返回:
        list[TextContent]: 工具执行结果，以文本形式返回
    
    执行流程:
        1. 调用验证中间件检查工具名称和参数
        2. 如果验证失败，返回错误信息
        3. 验证通过后，执行工具函数
        4. 捕获并处理执行过程中的异常
        5. 返回执行结果或错误信息
    """
    # 第一步: 验证工具调用
    # 使用 SecurityMiddleware 验证:
    # - 工具是否在白名单中
    # - 参数类型、格式、范围是否正确
    # - 是否包含危险字符
    result = security.check(tool_name=name, arguments=arguments, client_id="default")
    
    # 如果验证失败，记录日志并返回错误
    if not result["allowed"]:
        logger.warning(f"工具调用验证失败: name={name}, error={result['error']}")
        return [TextContent(type="text", text=f"验证失败: {result['error']}")]

    # 第二步: 执行工具
    for tool_config in loaded_tools:
        if tool_config["name"] == name:
            try:
                # 记录工具执行信息
                logger.info(f"执行工具: {name}, 参数: {arguments}")
                
                # 调用工具函数，传入参数
                result = tool_config["function"](**arguments)
                
                # 返回执行结果
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                # 捕获执行过程中的异常
                logger.error(f"工具执行错误: name={name}, error={str(e)}")
                return [TextContent(type="text", text=f"工具执行错误: {str(e)}")]
    
    # 如果工具不存在
    return [TextContent(type="text", text=f"工具 {name} 未找到")]


async def main():
    """
    主函数 - 启动 MCP 服务器
    
    使用 stdio 方式启动服务器，
    通过标准输入输出与客户端通信。
    这是 MCP 服务器的标准启动方式。
    """
    # 创建初始化选项
    options = server.create_initialization_options()
    
    # 启动 stdio 服务器
    async with stdio_server() as (read_stream, write_stream):
        # 运行服务器
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    # 启动服务器
    asyncio.run(main())