from typing import Iterator
from agno.agent import Agent
from agno.team import Team
from agno.workflow import Workflow, StepInput, StepOutput, Step
from agno.utils.pprint import pprint_run_response
from agno.run.workflow import WorkflowRunEvent, WorkflowRunOutputEvent
from  agno.models.openai import OpenAILike

from src.config.configs import get_llm_config
"""
Workflows are a powerful way to orchestrate your agents and teams.
They are a series of steps that are executed in a flow that you control.
"""

_llm_config = get_llm_config()
_llm = OpenAILike(
    id=_llm_config['id'],
    base_url=_llm_config['base_url'],
    api_key=_llm_config['api_key']
)

# === 定义工作流中所用到的Agents ===
research_agent = Agent(
    name="Research Agent",
    model=_llm,
    instructions="根据输入主题进行研究，并给出关键洞察，不依赖任何外部工具。",
)

summary_agent = Agent(
    name="Summary Agent",
    model=_llm,
    instructions="对研究内容做总结和提炼，形成结构化的 key insights。",
)

content_planner = Agent(
    name="Content Planner",
    model=_llm,
    instructions=[
        "基于研究内容生成为期4周的内容规划。",
        "每周生成 3 篇内容，给出标题+简介。",
    ],
)

# === 定义团队 ===
research_team = Team(
    name="Research Team",
    model=_llm,
    members=[research_agent, summary_agent],
    instructions="多个成员共同对主题进行分析、提炼与总结。",
)

def pre_outpus(step_input : StepInput) -> StepOutput:
    return StepOutput(
        content=f"Pre-outputs: {step_input.previous_step_outputs}"
    )

end_step = Step(
    name="End Step",
    executor=pre_outpus,
    description="查看先前步骤的输出结果"
)

# === 定义工作流 ===
workflow = Workflow(
    name="Simple Content Planning Workflow",
    description="本地可运行的内容研究 → 总结 → 内容规划流程",
    steps=[research_team, content_planner, end_step],
    debug_mode=True,
)

if __name__ == "__main__":
    try:
        response: Iterator[WorkflowRunOutputEvent]= workflow.run(
            input="2025 年 AI 趋势",
            markdown=True,
            stream=True,
        )

        for event in response:
            if event.event == WorkflowRunEvent.condition_execution_started.value:
                print(event)
                print()
            elif event.event == WorkflowRunEvent.condition_execution_completed.value:
                print(event)
                print()
            elif event.event == WorkflowRunEvent.workflow_started.value:
                print(event)
                print()
            elif event.event == WorkflowRunEvent.step_started.value:
                print(event)
                print()
            elif event.event == WorkflowRunEvent.step_completed.value:
                print(event)
                print()
            elif event.event == WorkflowRunEvent.workflow_completed.value:
                print(event)
                print()

        pprint_run_response(response, markdown=True)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()