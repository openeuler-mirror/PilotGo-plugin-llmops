import asyncio
import os
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.tools import tool
from agno.utils import pprint
from rich.console import Console
from rich.prompt import Prompt

from src.config.configs import get_llm_config

"""
The Model Context Protocol (MCP) enables Agents to interact with external systems through a standardized interface.
You can connect your Agents to any MCP server, using Agno’s MCP integration.
"""

from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

_llm_config = get_llm_config()
_llm = OpenAILike(
    id=_llm_config['id'],
    base_url=_llm_config['base_url'],
    api_key=_llm_config['api_key']
)

agno_tools = MCPTools(url="https://docs.agno.com/mcp", transport="streamable-http")
"""
server_params = StreamableHTTPClientParams(
    url=...,
    headers=...,
    timeout=...,
    sse_read_timeout=...,
    terminate_on_close=...,
)
"""

async def mcp_agno():
    await agno_tools.connect()

    try:
        # Setup and run the agent
        agent = Agent(model=_llm, debug_mode=True, tools=[agno_tools])
        await agent.aprint_response("What can you tell me about MCP support in Agno?", stream=True)

    finally:
        # Always close the connection when done
        await agno_tools.close()

async def github_agent(message: str) -> None:
    """Run the GitHub agent with the given message."""

    # Initialize the MCP server
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
    )

    # Create a client session to connect to the MCP server
    async with MCPTools(server_params=server_params) as agno_tools:
        agent = Agent(
            tools=[agno_tools],
            instructions=dedent("""\
                You are a GitHub assistant. Help users explore repositories and their activity.

                - Use headings to organize your responses
                - Be concise and focus on relevant information\
            """),
            markdown=True,
                    )

        # Run the agent
        await agent.aprint_response(message, stream=True)


# Example usage
if __name__ == "__main__":
    try:
        asyncio.run(mcp_agno())

        # Pull request example
        asyncio.run(
            github_agent(
                "Tell me about Agno. Github repo: https://github.com/agno-agi/agno. You can read the README for more information."
            )
        )

    except Exception as e:
        print(f"Error: {e}")