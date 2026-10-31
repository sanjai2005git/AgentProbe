"""
Agent Factory for instantiating architecture and model provider combinations.
"""

from typing import Union
from agentprobe.llm.base import BaseLLMProvider
from agentprobe.tools.registry import ToolRegistry
from agentprobe.agents.barebones_react import BarebonesReActAgent
from agentprobe.agents.langgraph_react import LangGraphReActAgent
from agentprobe.agents.plan_and_execute import PlanAndExecuteAgent

AgentInstance = Union[BarebonesReActAgent, LangGraphReActAgent, PlanAndExecuteAgent]


def create_agent(
    architecture: str,
    llm: BaseLLMProvider,
    tools: ToolRegistry,
) -> AgentInstance:
    """Factory function to build an agent instance given an architecture identifier."""
    arch = architecture.lower()
    if arch in ["barebones_react", "react", "barebones"]:
        return BarebonesReActAgent(llm=llm, tools=tools)
    elif arch in ["langgraph_react", "langgraph"]:
        return LangGraphReActAgent(llm=llm, tools=tools)
    elif arch in ["plan_and_execute", "plan_execute", "with_reflection"]:
        return PlanAndExecuteAgent(llm=llm, tools=tools)
    else:
        raise ValueError(
            f"Unknown architecture '{architecture}'. Available: 'barebones_react', 'langgraph_react', 'plan_and_execute'"
        )

