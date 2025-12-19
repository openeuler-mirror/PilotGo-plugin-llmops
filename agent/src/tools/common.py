from typing import List

from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.tools import Toolkit
from agno.utils.log import logger
from agno.tools import tool

from src.config.configs import get_llm_config
'''
Agents use tools to take actions and interact with external systems
Tools are functions that an Agent can run to achieve tasks.
For example: searching the web, running SQL, sending an email or calling APIs.
You can use any python function as a tool or use a pre-built Agno toolkit.
For more control, write your own python functions and add them as tools to an Agent.
'''

def get_agent_model(agent: Agent) -> str:
    """Get the model of the agent."""
    return agent.model.id

@tool(requires_confirmation=True)
def run_shell_command(args: List[str], tail: int = 100) -> str:
    """
    Runs a shell command and returns the output or error.

    Args:
        args (List[str]): The command to run as a list of strings.
        tail (int): The number of lines to return from the output.
    Returns:
        str: The output of the command.
    """
    import subprocess
    try:
        logger.info(f"Running shell command: {args}")
        result = subprocess.run(args, capture_output=True, text=True)
        logger.info(f"Result: {result}")
        logger.debug(f"Return code: {result.returncode}")
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        # return only the last n lines of the output
        return "\n".join(result.stdout.split("\n")[-tail:])
    except Exception as e:
        logger.warning(f"Failed to run shell command: {e}")
        return f"Error: {e}"

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
        tools=[get_agent_model],
    )
    agent.print_response("agent的使用的模型是什么？", stream=True)