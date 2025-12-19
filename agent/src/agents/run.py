import asyncio

from agno.agent import Agent, RunOutput
from agno.models.openai import OpenAILike
from agno.utils.pprint import pprint_run_response

from src.agents.build import create_agent
from src.config.configs import get_llm_config

async def async_run_agent(agent: Agent, query: str):
    # 异步运行agent
    response = await agent.arun(input=query)
    print(response.content)

_llm_config = get_llm_config()
_llm = OpenAILike(
    id=_llm_config['id'],
    base_url=_llm_config['base_url'],
    api_key=_llm_config['api_key']
)

if __name__ == "__main__":
    agent = create_agent(_llm)
    agent.print_response("你好！", stream=True)
    # # Run agent and return the response as a variable
    # # Print the response in markdown format
    response: RunOutput = agent.run("你好！")
    pprint_run_response(response, markdown=True)


