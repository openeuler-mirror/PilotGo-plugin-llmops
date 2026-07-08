import os
import sys
import importlib.util
import logging
import inspect
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('os-mcp')

mcp = FastMCP("os-mcp")


def load_and_register_tools():
    os_directory = os.path.join(os.path.dirname(__file__), 'os')
    registered_count = 0

    for root, _, files in os.walk(os_directory):
        for filename in files:
            if not filename.endswith('.py'):
                continue
            if filename.startswith('_') or filename.startswith('.'):
                continue

            file_path = os.path.join(root, filename)

            try:
                module_name = filename[:-3]
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if not hasattr(module, 'TOOL_CONFIG'):
                    continue

                config = module.TOOL_CONFIG
                tool_func = config["function"]
                tool_name = config["name"]
                tool_desc = config["description"]

                def wrapper(func, name):
                    async def inner(**kwargs):
                        try:
                            logger.info(f"执行工具: {name}, 参数: {kwargs}")
                            if inspect.iscoroutinefunction(func):
                                result = await func(**kwargs)
                            else:
                                result = func(**kwargs)
                            return str(result)
                        except Exception as e:
                            logger.error(f"工具执行错误: {name}, error={str(e)}")
                            return f"工具执行错误: {str(e)}"
                    return inner

                mcp.tool(name=tool_name, description=tool_desc)(wrapper(tool_func, tool_name))
                registered_count += 1

            except Exception as e:
                logger.error(f"加载工具 {file_path} 失败: {e}")

    logger.info(f"已注册 {registered_count} 个工具")


load_and_register_tools()


def main():
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()