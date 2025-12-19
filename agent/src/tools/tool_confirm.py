from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.tools import tool
from agno.utils import pprint
from rich.console import Console
from rich.prompt import Prompt

from src.tools.common import run_shell_command
from src.config.configs import get_llm_config

'''
This example demonstrates how to implement human-in-the-loop functionality
    by requiring user confirmation before executing sensitive tool operations.
'''
console = Console()

_llm_config = get_llm_config()
_llm = OpenAILike(
    id=_llm_config['id'],
    base_url=_llm_config['base_url'],
    api_key=_llm_config['api_key']
)
if __name__ == "__main__":
    llm_config = get_llm_config()
    agent = Agent(
        model=_llm,
        tools=[run_shell_command],
        markdown=True,
    )

    run_response = agent.run("查看当前目录下的所有文件")

    for requirement in run_response.tools_requiring_confirmation:   # ToolExecution
        # Ask for confirmation
        console.print(
            f"Tool name [bold blue]{requirement.tool_name}({requirement.tool_args})[/] requires confirmation."
        )
        message = (
            Prompt.ask("Do you want to continue?", choices=["y", "n"], default="y")
            .strip()
            .lower()
        )

        # Confirm or reject the requirement
        if message == "n":
            requirement.confirmed = False
        else:
            requirement.confirmed = True

    # Continue the run with updated tools
    # After setting confirmed=True/False on each requirement, pass the updated tools list
    if run_response.is_paused:
        run_response = agent.continue_run(
            run_response=run_response,
            updated_tools=requirement,
        )

    pprint.pprint_run_response(run_response)