import os
import importlib.util
import logging
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('os-mcp')

mcp = FastMCP("os-mcp")

loaded_tools = []


def load_tools_from_directory(directory: str):
    tools = []
    if not os.path.exists(directory):
        return tools

    for root, dirs, files in os.walk(directory):
        for filename in files:
            if (filename.endswith('.py') and 
                not filename.startswith('_') and 
                not filename.startswith('.') and
                '__' not in filename and
                'split_files' not in filename and
                filename != 'cmd_safety_guard.py'):
                module_name = filename[:-3]
                file_path = os.path.join(root, filename)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        if hasattr(module, 'TOOL_CONFIG'):
                            tools.append(module.TOOL_CONFIG)
                except Exception as e:
                    logger.error(f"加载工具 {file_path} 失败: {e}")

    return tools


def register_tools():
    global loaded_tools
    os_directory = os.path.join(os.path.dirname(__file__), 'os')
    loaded_tools = load_tools_from_directory(os_directory)

    for tool_config in loaded_tools:
        tool_name = tool_config["name"]
        tool_func = tool_config["function"]
        tool_desc = tool_config["description"]

        def make_wrapper(func, name):
            async def wrapper(**kwargs):
                try:
                    logger.info(f"执行工具: {name}, 参数: {kwargs}")
                    result = func(**kwargs)
                    return str(result)
                except Exception as e:
                    logger.error(f"工具执行错误: {name}, error={str(e)}")
                    return f"工具执行错误: {str(e)}"
            return wrapper

        wrapper_func = make_wrapper(tool_func, tool_name)
        mcp.tool(name=tool_name, description=tool_desc)(wrapper_func)

    logger.info(f"已注册 {len(loaded_tools)} 个工具")


register_tools()

if __name__ == "__main__":
    mcp.run(transport='stdio')